from setuptools import setup

requirements = []

setup(
    name='x32tunnel',
    use_scm_version=True,
    author="Karl Gutwin",
    author_email="karl@gutwin.org",
    description="X32 OSC TCP tunnel",
    packages=[
        'x32tunnel'
    ],
    entry_points={
        'console_scripts': ['x32tunnel=x32tunnel.cli:main']
    },
    python_requires='>=3.6',
    setup_requires=['setuptools_scm'],
    install_requires=requirements,
    classifiers=[
        'Programming Language :: Python :: 3'
    ]
)
