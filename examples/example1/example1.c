#include <stdio.h>
#include <math.h>

double scale_rotation_rate_ = 1.0;
double scale_forward_speed_ = 1.0;

void publish(double angular, double linear)
{
    printf("%.3f, %.3f", angular, linear);
}

int read_sensor(double *x, double *y)
{
    *x = 1.0;
    *y = 2.0;
    return 0;
}

void on_timer(void)
{
    double msg_angular_z;
    double msg_linear_x;
    double t_transform_translation_y, t_transform_translation_x;

    int result;
    result = read_sensor(&t_transform_translation_x, &t_transform_translation_y);
    if (result != 0)
        return;

    msg_angular_z = scale_rotation_rate_ * atan2(t_transform_translation_y, t_transform_translation_x);
    msg_linear_x = scale_forward_speed_ * sqrt(pow(t_transform_translation_x, 2) + pow(t_transform_translation_y, 2));

    publish(msg_angular_z, msg_linear_x);
}
