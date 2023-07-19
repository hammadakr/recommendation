"""
Read all approved users into a feather file (faster to read/write than csv)
BUT take the info for the user for which recommendation is being generated only from the request body
(since that user may not be approved)
this ensures only recommending approved users

On initial setup:
    [Write this in a python script]
    Query the database for all approved users, save into feather file
    Query the database for all interest activity, save into feather file

[Part of flask backend]
On server launch:
    Load user and interest dataframes from their feather files

On each recommend request:
    Update the database for that user (set lastonline to current time)

Every 15 mins (updation):
    Query the database for the last time updation happened

    Query the database for all users(approved or not) with lastonline after last updation
    update the live dataframe with the data of these (insert new, update existing)
    also for those with status == false, remove them from live dataframe

    Receive all interest activity with timestamp after last updation
    update the live dataframe with these (insertion only)
"""


"""
TODO
Implement the tasks for updating users and interests 
Implement the user deactivation and activation
Setup flask tests with pytest
figure out why 200 is not sent back to github
add extensive logging
documentation 

"""