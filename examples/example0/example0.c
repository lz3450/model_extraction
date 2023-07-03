#include <stdio.h>
#include <stdlib.h>

double scale_ = 1.0;

void publish(double msg)
{
    printf("%.3f", msg);
}

void on_timer(void)
{
    double msg = rand() * scale_;
    publish(msg);
}
