"""Currently possibly broken setup script for unused-argument


Note: Script does seem to work when run directly with pip:

        pip3 install .


      Pip install however does no longer work after uploading to pypi:

        python3 setup.py bdist
        twine upload dist/txjsonrpcqueue*.tar.gz
        cd ..
        pip3 install txjsonrpcqueue

        FIXME!

"""
from setuptools import setup, find_packages
setup(
    name='txjsonrpcqueue',
    version='0.1.2',
    description='Asynchronous JSON-RPC hysteresis-command-queue library.',
    long_description="""A simple asynchronous (both twisted and asyncio) Python library
    for communicating with JSON-RPC services. The prime target for txjsonrpcqueue is for
    use with the STEEM blockchain APPBASE JSON-RPC full-API nodes.""",
    url='https://github.com/pibara-utopian/txjsonrpcqueue/',
    author='Rob J Meijer',
    author_email='pibara@gmail.com',
    license='BSD',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 2',
        'Operating System :: OS Independent',
        'Environment :: Other Environment',
    ],
    keywords='jsonrpc twisted asyncio hysteresis queue steem steemit',
    install_requires=['twisted'],
    extras_require={
        'asyncio':  ["aiohttp"]
    },
    packages=find_packages()
)
