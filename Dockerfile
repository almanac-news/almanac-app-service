FROM python:2-onbuild
EXPOSE  3000
CMD [ "python", "./server/app.py" ]
