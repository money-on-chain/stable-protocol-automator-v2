import boto3
import os


def aws_put_metric_heart_beat(alarm_settings, value):

    if 'AWS_ACCESS_KEY_ID' not in os.environ:
        return

    # Create CloudWatch client
    cloudwatch = boto3.client('cloudwatch')

    # Put custom metrics
    cloudwatch.put_metric_data(
        MetricData=[
            {
                'MetricName': alarm_settings['metric_name'],
                'Dimensions': [
                    {
                        'Name': alarm_settings['dimensions_name'],
                        'Value': alarm_settings['dimensions_value']
                    },
                ],
                'Unit': 'None',
                'Value': value
            },
        ],
        Namespace=alarm_settings['namespace']
    )
