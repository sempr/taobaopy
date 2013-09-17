from setuptools import setup

__author__ = 'Sempr'


setup(
    name='taobaopy',
    version='3.6.0',
    url='https://github.com/sempr/taobaopy',
    license='BSD',
    author='Fred Wang',
    author_email='taobao-pysdk@1e20.com',
    description='A Very Easy Learned Python SDK For TaoBao.com API',
    long_description=__doc__,
    packages=['taobaopy'],
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=['requests >= 1.2.0'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
