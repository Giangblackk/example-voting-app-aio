from locust import HttpUser, TaskSet, task
from websocket import create_connection
from urllib.parse import urlparse
from random import randint


class VotingBehavior(TaskSet):
    def on_start(self) -> None:
        ws_uri = "ws://" + urlparse(self.user.host).netloc + "/result"
        self.ws = create_connection(ws_uri)

    def on_stop(self):
        self.ws.close()

    @task
    def vote_and_wait(self):
        # vote over http
        self.client.post(f"/vote/{randint(0,1)}")
        # wait over websocket
        self.ws.recv()


class VotingUser(HttpUser):
    tasks = [VotingBehavior]
