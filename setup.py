from setuptools import setup

__author__ = 'Sempr'


setup(
    name='taobaopy',
    version='2.0.1',
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
    install_requires=['pycurl'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
