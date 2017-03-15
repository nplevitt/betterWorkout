from flask import Flask, json, render_template, redirect, request
from flask_ask import Ask, statement, question, session, audio
import numpy as np
import json
import argparse

# Read in paths for S3 bucket and clock dictionary
parser = argparse.ArgumentParser()
parser.add_argument("-bucket", help="URL of S3 Bucket holding clock mp3s")
parser.add_argument("-clock_json", help="Path to File Containing Clock Dictionary")
args = parser.parse_args()

# Initialize list of possible workouts
workout_list = [
    'Pushups', 'Decline Pushup', 'Crunches', 'Wall Sits', 'Burpees', 'Jumping Jacks', 'Pushups with a Twist', 'Planks',
    'Stepups', 'Lunges', 'Squats', 'Calf Raises', 'Superman', 'Tricep Dips', 'Arm Circles',
    'Side Plank', 'Bicycle Kicks', 'Spiderman Plank']

# Read in clocks dictionary
with open(args.clock_json, 'r') as f:
    clocks = json.loads(f.read())


def getWorkout(num_min):
    """
    This function generates the random workout of a given length
    :param num_min: The length of the workout, in minutes
    :type num_min: Numeric
    :return: The workout as a list of tuples of (exercise, duration)
    """
    # Coerce the length in minutes to seconds, initialize max and min and list of all exercise durations.
    num_secs = 60.0 * num_min
    max_duration = (num_secs / 5)
    min_duration = (num_secs / 10)
    exercise_durations = np.arange(min_duration, max_duration + 30, 30)
    exercise_lengths = []

    # As long as there are seconds left to be filled, add an exercise to the workout
    while num_secs != 0:
        # Randomly choose a duration for the next exercise
        duration = exercise_durations[np.random.randint(0,len(exercise_durations))]
        # If the chosen duration is greater than the number of seconds left, set it to the number of seconds left.
        if duration > num_secs:
            duration = num_secs
        # Append the exercise duration and subtract it from the duration left to be filled.
        exercise_lengths.append(duration)
        num_secs -= duration

    # Initialize the empty exercise list and a
    exercises = []
    # Copy the list of possible exercises to a temporary list for manipulation
    tmp_workout_list = workout_list[:]
    # For every duration as selected above, add an exercise to pair with it
    for i in range(len(exercise_lengths)):
        # Choose a random exercise from the list of possible exercises
        exercise = tmp_workout_list[np.random.randint(0, len(tmp_workout_list))]
        exercises.append(exercise)
        # Remove the exercise from the temporary list so there are no exercises quickly repeated
        tmp_workout_list.remove(exercise)
        # If there are less than 6 exercises left in the temporary list, re-populate it with all the possible exercises
        if len(tmp_workout_list) < 6:
            tmp_workout_list = workout_list[:]
    # Zip together the exercises and their durations to return
    return zip(exercises, exercise_lengths)

# Initialize the Flask app
app = Flask(__name__)
ask = Ask(app, "/alexa")


@ask.launch
def new_ask():
    """
    This is the launch response.
    :return:
    """
    # Intialize the global "count" to -1
    session.attributes['count'] = -1
    # Get the start message more info responses from the YAML template
    start_message = render_template('start_message')
    more_info = render_template('more_info')
    # Return the start message, repromt with more info
    return question(start_message).reprompt(more_info)


@ask.intent('help')
def help():
    """
    This is the help intent, it is for returning more information on using the app.
    It can be triggered by saying "help"
    :return:
    """
    msg = render_template('more_info')
    return question(msg).reprompt(msg)


@ask.intent('startIntent')
def launchWorkout(num_min):
    """
    This is the start intent, it is for starting the workout.
    It can be triggered by saying "Start __ Minute Workout"
    :param num_min: The total duration of the workout, in minutes.
    :return:
    """
    # If the user does not specify a workout duration, reprompt with the misunderstood intent
    if num_min is None:
        msg = render_template('misunderstood')
        return question(msg)
    # Coerce number of minutes from string to integer
    num_min = int(num_min)
    # Initialize the global workout variable as the random workout
    session.attributes['workout'] = getWorkout(num_min)
    # Initialize the global count to 0
    session.attributes['count'] = 0
    # Get the start workout message and return it
    start_message = render_template('start_msg', num_min=num_min)
    return question(start_message)

@ask.intent('runExercise')
def runExercise():
    """
    This is the run exercise intent, it is for running the next exercise in the workout.
    It can be triggered by saying "Ready"
    :return:
    """
    # Get the global count variable
    cnt = session.attributes['count']
    # If the global count is -1, that means the workout has not been initialized, reprompt with misunderstood intent
    if cnt == -1:
        msg = render_template('misunderstood')
        retell = msg
    # Otherwise, run the next exercise
    else:
        # Get the next exercise and associated duration
        exercise, duration = session.attributes['workout'][cnt]
        try:
            # Get the workout that is coming up next, this is for including the information in the prompt
            next_exercise, tmp = session.attributes['workout'][cnt+1]
        # If the current exercise is the last one, this will trigger an index out of range error
        # In which case, set the next exercise to None
        except IndexError:
            next_exercise = None
        # Set the global exercise and duration variables to the next exercise and duration
        session.attributes['exercise'] = exercise
        session.attributes['duration'] = duration
        # Coerce duration to an integer
        # Get the associated clock for that duration
        clock = args.bucket + clocks[duration]
        # If the count is 0, this is the first exercise, send associated prompt.
        if cnt == 0:
            msg = render_template('first_exercise', exercise=exercise, duration=duration, clock=clock, next=next_exercise)
            retell = render_template('retell')

        # If the next exercise is None, then this is the last exercise, send associated prompt
        elif not next_exercise:
            return question(render_template('last_exercise', exercise=exercise, duration=duration, clock=clock))

        # Otherwise, prompt for the next exercise
        else:
            msg = render_template('next_exercise', exercise=exercise, duration=duration, clock=clock, next=next_exercise)
            retell = render_template('retell')

        # Iterate the global count
        session.attributes['count'] += 1

    return question(msg).reprompt(retell).simple_card(exercise, 'A brief description of {}'.format(exercise))


@ask.intent("finished")
def finished():
    """
    This is the workout finished intent.
    It is triggered when the user says "Finished"
    :return:
    """
    msg = render_template('finished')
    return statement(msg)

@ask.intent("noIntent")
def noIntent():
    """
    This is the intent if the user does not respond.
    :return:
    """
    msg = render_template('retell')
    return question(msg)

# Run the Flask App
if __name__ == '__main__':
    app.run(debug=True)