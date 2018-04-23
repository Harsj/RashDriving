#include <io/json_converters.hpp>

#include <iostream>

namespace pilotguru {
nlohmann::json PoseToJson(const ORB_SLAM2::Pose &pose) {
  nlohmann::json result;
  result[kTranslation] = {pose.translation(0), pose.translation(1),
                          pose.translation(2)};
  nlohmann::json rotation;
  rotation[kW] = pose.rotation.w();
  rotation[kX] = pose.rotation.x();
  rotation[kY] = pose.rotation.y();
  rotation[kZ] = pose.rotation.z();
  result[kRotation] = rotation;

  return result;
}

ORB_SLAM2::Pose JsonToPose(const nlohmann::json &pose_json) {
  ORB_SLAM2::Pose pose;

  const nlohmann::json &translation = pose_json[kTranslation];
  pose.translation(0) = translation.at(0);
  pose.translation(1) = translation.at(1);
  pose.translation(2) = translation.at(2);

  const nlohmann::json &rotation = pose_json[kRotation];
  pose.rotation.w() = rotation[kW];
  pose.rotation.x() = rotation[kX];
  pose.rotation.y() = rotation[kY];
  pose.rotation.z() = rotation[kZ];

  return pose;
}

void SetPlane(nlohmann::json *json_root, const cv::Mat &plane) {
  CHECK_EQ(plane.rows, 2);
  CHECK_EQ(plane.cols, 3);
  (*CHECK_NOTNULL(json_root))[kPlane] = {
      {plane.at<double>(0, 0), plane.at<double>(0, 1), plane.at<double>(0, 2)},
      {plane.at<double>(1, 0), plane.at<double>(1, 1), plane.at<double>(1, 2)}};
}

cv::Mat ReadPlane(const nlohmann::json &json_root) {
  cv::Mat plane(2, 3, CV_64F);
  const auto &plane_json = json_root[kPlane];
  for (size_t row : {0, 1}) {
    for (size_t col : {0, 1, 2}) {
      plane.at<double>(row, col) = plane_json.at(row).at(col);
    }
  }
  return plane;
}

void SetTrajectory(nlohmann::json *json_root,
                   const std::vector<ORB_SLAM2::PoseWithTimestamp> &trajectory,
                   const std::vector<cv::Mat> *projected_directions,
                   const vector<double> *turn_angles, int frame_id_offset) {
  CHECK_NOTNULL(json_root);
  if (projected_directions != nullptr) {
    CHECK_EQ(trajectory.size(), projected_directions->size());
  }
  if (turn_angles != nullptr) {
    CHECK_EQ(trajectory.size(), turn_angles->size());
  }
  (*json_root)[kTrajectory] = {};
  for (size_t point_idx = 0; point_idx < trajectory.size(); ++point_idx) {
    nlohmann::json point_json;
    const ORB_SLAM2::PoseWithTimestamp &point = trajectory.at(point_idx);
    point_json[kTimeUsec] = point.time_usec;
    point_json[kIsLost] = point.is_lost;
    point_json[kFrameId] = point.frame_id - frame_id_offset;
    point_json[kPose] = PoseToJson(point.pose);

    if (projected_directions != nullptr) {
      const cv::Mat &direction = projected_directions->at(point_idx);
      point_json[kPlanarDirection] = {direction.at<double>(0, 0),
                                      direction.at<double>(0, 1)};
    }
    if (turn_angles != nullptr) {
      if (point_idx == 0) {
        point_json[kAngularVelocity] = 0;
      } else {
        const double rotation_time_sec =
            static_cast<double>(point.time_usec -
                                trajectory.at(point_idx - 1).time_usec) *
            1e-6;
        point_json[kAngularVelocity] =
            turn_angles->at(point_idx) / (rotation_time_sec + 1e-10);
      }
    }

    (*json_root)[kTrajectory].push_back(point_json);
  }
}

void ParseTrajectory(const nlohmann::json &trajectory_json,
                     std::vector<ORB_SLAM2::PoseWithTimestamp> *trajectory,
                     std::vector<cv::Mat> *projected_directions,
                     vector<double> *turn_angles) {
  CHECK_NOTNULL(trajectory);
  CHECK(trajectory->empty());
  if (projected_directions != nullptr) {
    CHECK(projected_directions->empty());
  }
  if (turn_angles != nullptr) {
    CHECK(turn_angles->empty());
  }

  long prev_time_usec = trajectory_json[kTrajectory].front()[kTimeUsec];
  for (const auto &point_json : trajectory_json[kTrajectory]) {
    trajectory->emplace_back();
    ORB_SLAM2::PoseWithTimestamp &point = trajectory->back();
    point.pose = JsonToPose(point_json[kPose]);
    point.time_usec = point_json[kTimeUsec];
    point.is_lost = point_json[kIsLost];
    point.frame_id = point_json[kFrameId];

    if (projected_directions != nullptr) {
      projected_directions->emplace_back(1, 2, CV_64F);
      cv::Mat &direction = projected_directions->back();
      direction.at<double>(0, 0) = point_json[kPlanarDirection].at(0);
      direction.at<double>(0, 1) = point_json[kPlanarDirection].at(1);
    }

    if (turn_angles != nullptr) {
      const double interval_sec =
          static_cast<double>(point.time_usec - prev_time_usec) * 1e-6;
      const double angular_velocity = point_json[kAngularVelocity];
      turn_angles->push_back(angular_velocity * interval_sec);
      prev_time_usec = point.time_usec;
    }
  }
}

void ReadTrajectoryFromFile(
    const string &filename,
    std::vector<ORB_SLAM2::PoseWithTimestamp> *trajectory,
    cv::Mat *horizontal_plane, std::vector<cv::Mat> *projected_directions,
    vector<double> *turn_angles) {
  std::vector<ORB_SLAM2::PoseWithTimestamp> result;

  std::ifstream trajectory_istream(filename);
  nlohmann::json trajectory_json;
  trajectory_istream >> trajectory_json;

  ParseTrajectory(trajectory_json, trajectory, projected_directions,
                  turn_angles);

  if (horizontal_plane != nullptr) {
    *horizontal_plane = ReadPlane(trajectory_json);
  }
}

void WriteTrajectoryToFile(
    const string &filename,
    const std::vector<ORB_SLAM2::PoseWithTimestamp> &trajectory,
    const cv::Mat *horizontal_plane,
    const std::vector<cv::Mat> *projected_directions,
    const vector<double> *turn_angles, int frame_id_offset) {
  nlohmann::json trajectory_json;
  pilotguru::SetTrajectory(&trajectory_json, trajectory, projected_directions,
                           turn_angles, 0);
  if (horizontal_plane != nullptr) {
    pilotguru::SetPlane(&trajectory_json, *horizontal_plane);
  }
  std::ofstream trajectory_ostream(filename);
  trajectory_ostream << trajectory_json.dump(2) << std::endl;
}

std::unique_ptr<nlohmann::json> ReadJsonFile(const std::string &filename) {
  std::ifstream file_stream(filename);
  std::unique_ptr<nlohmann::json> result(new nlohmann::json());
  file_stream >> *result;
  return std::move(result);
}

void WriteJsonFile(const nlohmann::json &data, const std::string &filename) {
  std::ofstream json_ostream(filename);
  json_ostream << data.dump(2) << std::endl;
}

void JsonWriteTimestampedRealData(const std::vector<long> &times_usec,
                                  const std::vector<double> &values,
                                  const std::string &filename,
                                  const std::string &root_element_name,
                                  const std::string &value_name) {
  CHECK_EQ(times_usec.size(), values.size());

  nlohmann::json out_json;
  out_json[root_element_name] = {};
  auto &out_events = out_json[root_element_name];
  for (size_t event_idx = 0; event_idx < values.size(); ++event_idx) {
    nlohmann::json event_json;
    event_json[pilotguru::kTimeUsec] = times_usec.at(event_idx);
    event_json[value_name] = values.at(event_idx);
    out_events.push_back(event_json);
  }
  std::ofstream json_ostream(filename);
  json_ostream << out_json.dump(2) << std::endl;
}
}
