from setuptools import setup, find_packages


setup(
    name='async_mqtt_publisher',
    description='MQTT publisher based on aiohttp',
    version='0.0.7',
    license='MIT',
    author="Alexey Dergunov",
    author_email='dergunovalexey2000@gmail.com',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    url='https://github.com/thealexeydergunov/async_mqtt_publisher.git',
    keywords='MQTT publisher based on aiohttp',
    install_requires=[
        'aiohttp',
    ],
)
