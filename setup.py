from setuptools import setup

setup(
    name = 'tangram_bundler',
    url = 'https://github.com/tangrams/bundler',
    version = 0.1,
    install_requires = [
        'PyYAML == 3.12'
    ],
    packages = [
        'tangram_bundler'
    ],
    entry_points = dict(
        console_scripts = [
            'tangram-bundle=tangram_bundler:main'
        ]
    )
)
