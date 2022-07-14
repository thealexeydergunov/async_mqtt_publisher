from setuptools import setup, find_packages


setup(
    name='async_mqtt_publisher',
    version='0.0.0',
    license='MIT',
    author="Alexey Dergunov",
    author_email='dergunovalexey2000@gmail.com',
    packages=find_packages('async_mqtt_publisher'),
    package_dir={'': 'async_mqtt_publisher'},
    url='https://github.com/thealexeydergunov/async_mqtt_publisher.git',
    keywords='MQTT publisher based on aiohttp',
    install_requires=[
        'aiohttp',
    ],
)
