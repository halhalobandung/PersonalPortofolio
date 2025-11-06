import os
import time
from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
from werkzeug.utils import secure_filename

