#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.emoji_smith_stack import EmojiSmithStack

app = cdk.App()
EmojiSmithStack(app, "EmojiSmithStack")

app.synth()