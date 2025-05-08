from setuptools import setup, find_packages

setup(
    name="common_utils",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",  # 添加 logger_client 需要的依賴
    ],
    author="pinyun",
    author_email="huangp585@gmail.com",
    description="Common utilities for microservices",
)
