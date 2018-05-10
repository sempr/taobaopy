from setuptools import setup

__author__ = 'Sempr'


setup(
    name='taobaopy',
    version='5.0.2',
    url='https://github.com/sempr/taobaopy',
    license='BSD',
    author='Sempr Wang',
    author_email='taobao-pysdk@1e20.com',
    description='A Very Easy Learned Python SDK For TaoBao.com API',
    long_description=__doc__,
    packages=['taobaopy'],
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=['requests>=2.18.4', 'six>=1.11.0,<2.0'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6'
    ]
)
