from setuptools import setup

setup(
    name = 'tangram_bundler',
    url = 'https://github.com/tangrams/bundler',
    version = 0.7,
    install_requires = [
        'PyYAML == 5.4'
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
