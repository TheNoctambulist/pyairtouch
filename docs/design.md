# Pyairtouch Design

This document describes some of the key design decisions made when implementing the `pyairtouch` library along with their rationale.

## TCP Connection Monitoring

### Context
Real world usage of the API has highlighted that, while some environments can happily maintain the open idle connection for long periods of time, there are situations where the idle connection will "crash" quite frequently.
Therefore, there is a need for `pyairtouch` to be robust against [half-open](https://en.wikipedia.org/wiki/TCP_half-open) connections.

In particular we want to ensure that when a client sends a command to the AirTouch it is reliably delivered.
Any dropped commands would force the client to implement complex retry logic.

When communicating via a TCP socket, the only way to reliably detect a half-open connection is to write data to the socket.
Neither the AirTouch 4 not AirTouch 5 interface specifications include any form of heartbeat mechanism.
The protocol also doesn't have any defined periodic messages which could be monitored for timeout.
However, there are several messages in the interface that can be sent at any time to request the latest status from the AirTouch.

### Design
In order to provide the desired command delivery guarantees and ensure that status updates are received even if no command is sent, a two-pronged approach is used:
1. Periodically send a request to the AirTouch as a heartbeat; and
2. Retry sending of commands for a short time if a re-connection is required when sending.

### Heartbeat
The Console Version Request (0xFF30) is used as the heartbeat for bot the AirTouch 4 and the AirTouch 5.
The Console Version Request has the advantage of being one of the smallest messages in the interface specifications, which results in low overhead.
Periodically requesting the Console Version also ensures timely notification when console updates are available.

The purpose of the heartbeat is primarily to keep the connection from being considered idle by any intermidiate devices on the network that may time out the connection (e.g. firewalls).
For this reason, the heartbeat interval can be fairly large.
A heartbeat interval of 300 seconds (5 minutes) has been selected based on the assumption that this will be less than typical firewall idle timeouts (which reading suggests typically default to 60 minutes).

The heartbeat response timeout is set to `heartbeat_interval + 30.0` seconds.
This allows the AirTouch up to 30 seconds to process the heartbeat and send a response.
Loss of a single heartbeat response is considered enough to trigger a connection reset.
Connection reset consits of closing the current TCP connection and attempting to re-establish a new connection.

### Retries
Many of the commands that can be sent to the AirTouch system are idempotent.
For example an AC Control command to turn the AC on, will have no effect if the AC is already turned on.
If an error occurs when sending an idempotent command we can safely retry sending that message.
If the message had actually been sent before the error occurred no ill-effects will be observed from sending it again.
Enabling retries in this manner provides improved reliabilty of commanding the AirTouch into a desired state in the event of a half-open connection or other similar error conditions.

To support these retries, the `AirTouchSocket` class is implemented with a message queue.
When a message is sent, clients of the `AirTouchSocket` need to provide a retry policy.
The retry policy defines the following properties:
* `max_retries` for the maximum number of times to retry the message after a failed send; and
* `max_lifetime` for the maximum duration to retain the message in the retry queue.

The combination of these two properties ensures that a bad message will not get stuck in an infinite retry loop.
They also ensure that if the connection is down for a long period of time, unexpected commands will not be sent through when the connection eventually does come back up.

A set of default retry policies have been defined to cover the common use cases:

 Policy                | Description 
-----------------------|------------------------------------------------
`RETRY_IDEMPOTENT`     | Used for idempotent commands.<br>Allows multiple retries within a 30 second interval.
`RETRY_NON_IDEMPOTENT` | Used for non-idempotent commands.<br>Prevents retries, but allows the message to be queued for 30 seconds.
`RETRY_CONNECTED`      | Used for messages that are only sent while the socket is connected.<br>Prevents retries and has a short lifetime.

It is the responsiblity of the `api` implementation for each AirTouch version to identify an appropriate retry policy for each command.

## AirTouch 4 Group Status Messages
The interface specification states that Group Status updates will be published whenever the group status changes.
However, real-world testing has shown that the AirTouch 4 console seems to get into a state where the Group Status updates stop being published until a Group Control is sent.
This has been observed even while the AC is turned on and the zones are active.

As a work-around, the AirTouch 4 API implementation includes a Group Status timeout.
When no group status messages have been received for 5 minutes, a request is sent to obtain the latest status.
Typical update intervals when house temperatures are stable and the AC is not running can be much longer than 5 minutes.
However, 5 minutes has been selected to ensure smooth temperature profiles in all scenarios.
If the Group Status received in response to the request is identical to the current status it will be ignored, so the only consequence of sending more frequent queries is increased network traffic.
