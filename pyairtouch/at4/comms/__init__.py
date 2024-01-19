"""AirTouch 4 implementation of the communication interfaces.

Implementation is in accordance with v1.6 of the communication protocol.
"""

MAX_GROUP_NUMBER = 15
"""The maximum group number in messages that include group numbers.

The valid range of group numbers is from 0 to this upper limit (inclusive).
"""
