#include <cstdlib>

#include <gflags/gflags.h>
#include <glog/logging.h>

#include <io/json_converters.hpp>
#include <slam/horizontal_flatten.hpp>
#include <slam/smoothing.hpp>

DEFINE_string(trajectory_in_file, "", "");
DEFINE_int64(sigma, -1, "");
DEFINE_string(trajectory_out_file, "", "");

int main(int argc, char **argv) {
  google::InitGoogleLogging(argv[0]);
  google::ParseCommandLineFlags(&argc, &argv, true);
  google::InstallFailureSignalHandler();

  CHECK(!FLAGS_trajectory_in_file.empty());
  CHECK(!FLAGS_trajectory_out_file.empty());
  CHECK_GT(FLAGS_sigma, 0);

  std::vector<ORB_SLAM2::PoseWithTimestamp> trajectory;
  cv::Mat horizontal_plane;
  pilotguru::ReadTrajectoryFromFile(FLAGS_trajectory_in_file, &trajectory,
                                    &horizontal_plane, nullptr, nullptr);

  pilotguru::SmoothHeadingDirections(&trajectory, FLAGS_sigma);
  std::unique_ptr<std::vector<cv::Mat>> projected_directions =
      pilotguru::ProjectDirections(trajectory, horizontal_plane);
  const vector<double> turn_angles =
      pilotguru::Projected2DDirectionsToTurnAngles(*projected_directions);

  pilotguru::WriteTrajectoryToFile(FLAGS_trajectory_out_file, trajectory,
                                   &horizontal_plane,
                                   projected_directions.get(), &turn_angles, 0);

  return EXIT_SUCCESS;
}