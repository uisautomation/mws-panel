from setuptools import setup

setup(
    name='vmmanager',
    version='0.1',
    py_modules=['vmmanager'],
    include_package_data=True,
    install_requires=[
        'click',
        'jsonschema',
        'py2-ipaddress',
    ],
    entry_points='''
        [console_scripts]
        vmmanager=vmmanager:cli
    ''',
)
