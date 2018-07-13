#include <cstdlib>

#include <gflags/gflags.h>
#include <glog/logging.h>

#include <json.hpp>

#include <interpolation/align_time_series.hpp>
#include <io/json_converters.hpp>
#include <optimization/gradient_descent.hpp>
#include <optimization/loss_function.hpp>
#include <optimization/optimizer.hpp>

DEFINE_string(locations_json, "", "GPS locations and velocities log.");
DEFINE_string(frames_json, "", "Video frames timestamps log.");
DEFINE_double(sigma, 0.5,
              "Gaussian smoothing kernel standard deviation, in seconds.");
DEFINE_string(out_json, "",
              "Copy of frames data with added interpolated velocities.");

DEFINE_double(l1_weight, 0.0, "");
DEFINE_double(l2_weight, 0.0, "");
DEFINE_double(distance_weight, 1.0, "");
DEFINE_double(accelerations_weight, 1.0, "");
DEFINE_double(accelerations_smoothness_weight, 1.0, "");
DEFINE_double(lr, 1e-1, "");
DEFINE_double(decay, 1.0, "");
DEFINE_double(iters, 1000, "");

namespace {
struct TimestampedVelocity {
  double velocity;
  long time_usec;
};

double IntervalInSeconds(long start_time_usec, long end_time_usec) {
  return static_cast<double>(end_time_usec - start_time_usec) * 1e-6;
}

std::vector<std::vector<pilotguru::InterpolationInterval>>
MakeGPSIndexToInterpolatedIntervals(
    const std::vector<TimestampedVelocity> &gps_velocities,
    const std::vector<long> &interpolation_timestamps) {
  std::vector<long> gps_timestamps;
  for (const TimestampedVelocity &gps : gps_velocities) {
    gps_timestamps.push_back(gps.time_usec);
  }

  return pilotguru::MakeInterpolationIntervals(gps_timestamps,
                                               interpolation_timestamps);
}

class GPSInterpolationObjective : public pilotguru::LossFunction {
public:
  GPSInterpolationObjective(
      const std::vector<TimestampedVelocity>
          &gps_velocities /* must be sorted by time */,
      const std::vector<long>
          &interpolation_timestamps /* must be sorted by time */,
      double l1_weight, double l2_weight, double velocity_penalty_weight,
      double acceleration_penalty_weight, double acceleration_smoothness_weight)
      : gps_velocities_(gps_velocities),
        interpolation_timestamps_(interpolation_timestamps),
        l1_weight_(l1_weight), l2_weight_(l2_weight),
        velocity_penalty_weight_(velocity_penalty_weight),
        acceleration_penalty_weight_(acceleration_penalty_weight),
        acceleration_smoothness_weight_(acceleration_smoothness_weight),
        gps_to_interpolated_intervals_(MakeGPSIndexToInterpolatedIntervals(
            gps_velocities, interpolation_timestamps)) {
    CHECK_GE(l1_weight_, 0.0);
    CHECK_GE(l2_weight_, 0.0);
    CHECK_GT(l1_weight_ + l2_weight_, 0.0);
    CHECK_GE(velocity_penalty_weight_, 0.0);
    CHECK_GE(acceleration_penalty_weight_, 0.0);
  }

  // Initializes the interpolated velocities to average gps velocities at their
  // respecive times.
  std::vector<double> InitToAverages() const {
    std::vector<double> result(interpolation_timestamps_.size(), 0.0);
    for (size_t gps_idx = 0; gps_idx < gps_velocities_.size(); ++gps_idx) {
      for (const pilotguru::InterpolationInterval &i :
           gps_to_interpolated_intervals_.at(gps_idx)) {
        result.at(i.interpolation_end_time_index) =
            gps_velocities_.at(gps_idx).velocity;
      }
    }
    return result;
  }

  double eval(const std::vector<double> &in,
              std::vector<double> *gradient) override {
    // Sanity checks.
    CHECK_NOTNULL(gradient);
    CHECK_EQ(in.size(), interpolation_timestamps_.size());
    CHECK_EQ(in.size(), gradient->size());

    for (size_t i = 0; i < gradient->size(); ++i) {
      gradient->at(i) = 0.0;
    }

    double objective = 0.0;

    // Distance match and gradients.
    for (size_t gps_index = 0; gps_index < gps_velocities_.size();
         ++gps_index) {
      const std::vector<pilotguru::InterpolationInterval> &intervals =
          gps_to_interpolated_intervals_.at(gps_index);
      double integrated_distance = 0, gps_duration = 0;
      for (const pilotguru::InterpolationInterval &interval : intervals) {
        integrated_distance += in.at(interval.interpolation_end_time_index) *
                               interval.DurationSec();
        gps_duration += interval.DurationSec(); // TODO factor out.
      }

      const double gps_distance =
          gps_velocities_.at(gps_index).velocity * gps_duration;
      const double distance_diff = integrated_distance - gps_distance;
      const double distance_diff_sign = distance_diff > 0 ? 1.0 : -1.0;

      objective +=
          l1_weight_ * velocity_penalty_weight_ * std::abs(distance_diff);
      objective +=
          l2_weight_ * velocity_penalty_weight_ * distance_diff * distance_diff;

      // Gradient of the travelled distance mismatch wrt the interpolated
      // velocities.
      for (const pilotguru::InterpolationInterval &interval : intervals) {
        gradient->at(interval.interpolation_end_time_index) +=
            l1_weight_ * velocity_penalty_weight_ * distance_diff_sign *
            interval.DurationSec();
        gradient->at(interval.interpolation_end_time_index) +=
            2.0 * l2_weight_ * velocity_penalty_weight_ * distance_diff *
            interval.DurationSec();
      }
    }

    // Accelerations.
    for (size_t i = 1; i < interpolation_timestamps_.size(); ++i) {
      const double inverse_duration =
          1.0 / IntervalInSeconds(interpolation_timestamps_.at(i - 1),
                                  interpolation_timestamps_.at(i));
      const double acceleration = (in.at(i) - in.at(i - 1)) * inverse_duration;
      const int acceleration_sign = acceleration > 0 ? 1 : -1;

      objective +=
          l1_weight_ * acceleration_penalty_weight_ * std::abs(acceleration);
      objective += l2_weight_ * acceleration_penalty_weight_ * acceleration *
                   acceleration;

      gradient->at(i - 1) -= l1_weight_ * acceleration_penalty_weight_ *
                             acceleration_sign * inverse_duration;
      gradient->at(i - 1) -= 2.0 * l2_weight_ * acceleration_penalty_weight_ *
                             acceleration * inverse_duration;

      gradient->at(i) += l1_weight_ * acceleration_penalty_weight_ *
                         acceleration_sign * inverse_duration;
      gradient->at(i) += 2.0 * l2_weight_ * acceleration_penalty_weight_ *
                         acceleration * inverse_duration;
    }

    // Accelerations smoothness.
    for (size_t i = 1; i < interpolation_timestamps_.size() - 1; ++i) {
      const double inverse_duration_prev =
          1.0 / IntervalInSeconds(interpolation_timestamps_.at(i - 1),
                                  interpolation_timestamps_.at(i));
      const double inverse_duration_next =
          1.0 / IntervalInSeconds(interpolation_timestamps_.at(i),
                                  interpolation_timestamps_.at(i + 1));
      const double acceleration_prev =
          (in.at(i) - in.at(i - 1)) * inverse_duration_prev;
      const double acceleration_next =
          (in.at(i + 1) - in.at(i)) * inverse_duration_next;
      const double acceleration_diff = acceleration_next - acceleration_prev;
      const int acceleration_sign = acceleration_diff > 0 ? 1 : -1;

      objective += l1_weight_ * acceleration_smoothness_weight_ *
                   std::abs(acceleration_diff);
      objective += l2_weight_ * acceleration_smoothness_weight_ *
                   acceleration_diff * acceleration_diff;

      gradient->at(i - 1) += l1_weight_ * acceleration_smoothness_weight_ *
                             acceleration_sign * inverse_duration_prev;
      gradient->at(i - 1) += 2.0 * l2_weight_ *
                             acceleration_smoothness_weight_ *
                             acceleration_diff * inverse_duration_prev;

      gradient->at(i + 1) += l1_weight_ * acceleration_smoothness_weight_ *
                             acceleration_sign * inverse_duration_next;
      gradient->at(i + 1) += 2.0 * l2_weight_ *
                             acceleration_smoothness_weight_ *
                             acceleration_diff * inverse_duration_next;

      gradient->at(i) -= l1_weight_ * acceleration_smoothness_weight_ *
                         acceleration_sign *
                         (inverse_duration_prev + inverse_duration_next);
      gradient->at(i) -= 2.0 * l2_weight_ * acceleration_smoothness_weight_ *
                         acceleration_diff *
                         (inverse_duration_prev + inverse_duration_next);
    }

    return objective;
  }

private:
  const std::vector<TimestampedVelocity> &gps_velocities_;
  const std::vector<long> &interpolation_timestamps_;
  const double l1_weight_, l2_weight_;
  const double velocity_penalty_weight_, acceleration_penalty_weight_,
      acceleration_smoothness_weight_;

  const std::vector<std::vector<pilotguru::InterpolationInterval>>
      gps_to_interpolated_intervals_;
};
} // namespace

int main(int argc, char **argv) {
  google::InitGoogleLogging(argv[0]);
  google::ParseCommandLineFlags(&argc, &argv, true);
  google::InstallFailureSignalHandler();

  CHECK(!FLAGS_locations_json.empty());
  CHECK(!FLAGS_frames_json.empty());
  CHECK(!FLAGS_out_json.empty());

  // Read raw GPS data.
  std::unique_ptr<nlohmann::json> locations_json =
      pilotguru::ReadJsonFile(FLAGS_locations_json);
  const auto &locations = (*locations_json)[pilotguru::kLocations];
  CHECK(!locations.empty());

  // Read raw frame timestamps data.
  std::unique_ptr<nlohmann::json> frames_json =
      pilotguru::ReadJsonFile(FLAGS_frames_json);
  const auto &frames = (*frames_json)[pilotguru::kFrames];
  CHECK(!frames.empty());

  // To reduce precision loss when converting to double timestamps, subtract the
  // earliest timestamp of the two time series from all the timestamps.
  const long locations_start_usec = locations.at(0)[pilotguru::kTimeUsec];
  const long frames_start_usec = frames.at(0)[pilotguru::kTimeUsec];
  const long start_usec = std::min(locations_start_usec, frames_start_usec);

  // GPS data to vectors.
  std::vector<double> gps_velocities, gps_timestamps;
  for (const nlohmann::json &location : locations) {
    gps_velocities.push_back(location[pilotguru::kSpeedMS]);
    const long time_usec = location[pilotguru::kTimeUsec];
    gps_timestamps.push_back(static_cast<double>(time_usec - start_usec) *
                             1e-6);
  }

  // Frame timestamps to vector.
  std::vector<double> frame_timestamps;
  std::vector<long> frame_timestamps_usec;
  for (const nlohmann::json &frame : frames) {
    const long time_usec = frame[pilotguru::kTimeUsec];
    frame_timestamps_usec.push_back(time_usec);
    frame_timestamps.push_back(static_cast<double>(time_usec - start_usec) *
                               1e-6);
  }

  std::vector<TimestampedVelocity> gps_data;
  for (const nlohmann::json &location : locations) {
    gps_data.push_back(
        {location[pilotguru::kSpeedMS], location[pilotguru::kTimeUsec]});
  }

  GPSInterpolationObjective loss(
      gps_data, frame_timestamps_usec, FLAGS_l1_weight, FLAGS_l2_weight,
      FLAGS_distance_weight, FLAGS_accelerations_weight,
      FLAGS_accelerations_smoothness_weight);
  pilotguru::GradientDescent optimizer(
      FLAGS_lr, FLAGS_decay, -10 /* min grad clip */, 10 /* max grad clip */);
  std::vector<double> params = loss.InitToAverages();
  optimizer.optimize(loss, &params, FLAGS_iters /* iters */);

  std::vector<double> grad(params.size(), 0.0);
  loss.eval(params, &grad);

  // Write out results.
  nlohmann::json result_json;
  result_json[pilotguru::kFrames] = {};
  for (size_t frame_idx = 0; frame_idx < frames.size(); ++frame_idx) {
    nlohmann::json frame_data = frames.at(frame_idx);
    frame_data[pilotguru::kSpeedMS] = params.at(frame_idx);
    result_json[pilotguru::kFrames].push_back(frame_data);
  }
  std::ofstream result_ostream(FLAGS_out_json);
  result_ostream << result_json.dump(2) << std::endl;

  return EXIT_SUCCESS;
}
