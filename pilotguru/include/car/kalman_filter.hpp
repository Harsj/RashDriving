#ifndef PILOTGURU_CAR_KALMAN_FILTER_HPP_
#define PILOTGURU_CAR_KALMAN_FILTER_HPP_

#include <Eigen/Dense>

#include <car/timestamped_history.hpp>

namespace pilotguru {
template <int Dims> struct KalmanFilterEstimateValue {
  // Eigen::DontAlign required because of
  // http://eigen.tuxfamily.org/dox-devel/group__TopicStructHavingEigenMembers.html
  Eigen::Matrix<double, Dims, 1, Eigen::DontAlign> mean;
  Eigen::Matrix<double, Dims, Dims, Eigen::DontAlign> covariance;
};

// 1D Kalman filter estimating the value and its speed of change (first time
// derivative), assuming that the acceleration (second derivative is random
// Gaussian distributed).
// Details at
// https://en.wikipedia.org/wiki/Kalman_filter#Example_application.2C_technical
//
// Observation model is unbiased with Gaussian noise.
class KalmanFilter1D {
public:
  typedef KalmanFilterEstimateValue<2> EstimateValue;

  KalmanFilter1D(double observation_variance,
                 double perturbation_variance_per_second);

  void Update(const Timestamped<double> &observation);
  const Timestamped<EstimateValue> &LatestEstimate() const;

private:
  const double observation_variance_, sqrt_perturbation_variance_per_second_;
  const Eigen::RowVector2d observation_matrix_;
  bool has_estimate_ = false;
  Timestamped<EstimateValue> latest_estimate_;
};

// Second-order 1D Kalman filter, modeling both first and second derivative of
// the observed quantity.
class KalmanFilter1D2Order {
public:
  typedef KalmanFilterEstimateValue<3> EstimateValue;

  KalmanFilter1D2Order(double observation_variance,
                       double perturbation_variance_per_second);

  void Update(const Timestamped<double> &observation);
  const Timestamped<EstimateValue> &LatestEstimate() const;

private:
  const double observation_variance_, sqrt_perturbation_variance_per_second_;
  const Eigen::RowVector3d observation_matrix_;
  bool has_estimate_ = false;
  Timestamped<EstimateValue> latest_estimate_;
};
} // namespace pilotguru

#endif // PILOTGURU_CAR_KALMAN_FILTER_HPP_
