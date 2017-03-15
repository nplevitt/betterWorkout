from flask import Flask, json, render_template, redirect, request
from flask_ask import Ask, statement, question, session, audio
import json
import requests
import time
import unidecode
import numpy as np
import time
import json

workout_list = [
    'Pushups', 'Decline Pushup', 'Crunches', 'Wall Sits', 'Burpees', 'Jumping Jacks', 'Pushups with a Twist', 'Planks',
    'Stepups', 'Lunges', 'Squats', 'Calf Raises', 'Superman', 'Tricep Dips', 'Arm Circles',
    'Side Plank', 'Bicycle Kicks', 'Spiderman Plank']

# clock_url = 'https://nplevitt.s3.amazonaws.com/clocks/'
#
# clocks = {30: clock_url+'clock30.mp3',
#           60: clock_url+'clock60.mp3',
#           90: clock_url+'clock60.mp3',
#           120: clock_url+'clock60.mp3',
#           150: clock_url+'clock60.mp3',
#           180: clock_url+'clock60.mp3',
#           210: clock_url+'clock60.mp3',
#           240: clock_url+'clock60.mp3',
#           270: clock_url+'clock60.mp3',
#           300: clock_url+'clock60.mp3',
#           330: clock_url+'clock60.mp3'}




def getWorkout(num_min):
    num_secs = 60.0 * num_min
    max_duration = (num_secs / 5)
    min_duration = (num_secs / 10)
    exercise_lengths = []

    while num_secs != 0:
        exercise_durations = np.arange(min_duration, max_duration+30, 30)
        duration = exercise_durations[np.random.randint(0,len(exercise_durations))]

        if duration > num_secs:
            duration = num_secs

        exercise_lengths.append(duration)
        num_secs -= duration

    exercises = []
    tmp_workout_list = workout_list[:]
    for i in range(len(exercise_lengths)):
        exercise = tmp_workout_list[np.random.randint(0, len(tmp_workout_list))]
        exercises.append(exercise)
        tmp_workout_list.remove(exercise)
        if len(tmp_workout_list) < 6:
            tmp_workout_list = workout_list[:]

    return zip(exercises, exercise_lengths)

app = Flask(__name__)
ask = Ask(app, "/alexa")


@ask.launch
def new_ask():
    session.attributes['count'] = -1
    start_message = render_template('start_message')
    more_info = render_template('more_info')
    return question(start_message).reprompt(more_info)


@ask.intent('help')
def help():
    msg = render_template('more_info')
    return question(msg).reprompt(msg)


@ask.intent('startIntent')
def launchWorkout(num_min):
    if num_min is None:
        msg = render_template('misunderstood')
        return question(msg)
    num_min = int(num_min)
    session.attributes['workout'] = getWorkout(num_min)
    session.attributes['count'] = 0
    start_message = render_template('start_msg', num_min=num_min)
    return question(start_message)

@ask.intent('runExercise')
def runExercise():
    cnt = session.attributes['count']

    if cnt == -1:
        msg = render_template('misunderstood')
        retell = msg

    else:
        exercise, duration = session.attributes['workout'][cnt]
        try:
            next_exercise, tmp = session.attributes['workout'][cnt+1]
        except IndexError:
            next_exercise = None
        session.attributes['exercise'] = exercise
        session.attributes['duration'] = duration
        dur = int(duration)
        clock = clocks[dur]

        if cnt == 0:
            msg = render_template('first_exercise', exercise=exercise, duration=dur, clock=clock, next=next_exercise)
            retell = render_template('retell')

        elif cnt == (len(session.attributes['workout']) - 1):
            return question(render_template('last_exercise', exercise=exercise, duration=dur, clock=clock))

        else:
            msg = render_template('next_exercise', exercise=exercise, duration=dur, clock=clock, next=next_exercise)
            retell = render_template('retell')

        session.attributes['count'] += 1

    return question(msg).reprompt(retell).simple_card(exercise, 'A brief description of {}'.format(exercise))


@ask.intent("finished")
def finished():
    msg = render_template('finished')
    return statement(msg)

@ask.intent("noIntent")
def noIntent():
    msg = render_template('retell')
    return question(msg)


if __name__ == '__main__':
    app.run(debug=True)