from setuptools import setup

__author__ = 'Sempr'


setup(
    name='taobaopy',
    version='5.0.0',
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
    install_requires=['requests>=2.18.4', 'six==1.11.0', 'urllib3==1.22'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
