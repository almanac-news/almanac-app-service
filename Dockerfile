FROM python:2-onbuild

RUN nosetests -v --with-coverage --cover-inclusive --cover-package=server

EXPOSE  5000
CMD [ "python", "./server/app.py" ]
