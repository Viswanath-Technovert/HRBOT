#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

class DefaultConfig:
    """ Bot Configuration """

    PORT = 3978
    APP_ID = os.environ.get("MicrosoftAppId", "42bb93cb-acdb-47b5-9b77-97201641a9da")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "oUt8Q~sQb1kESENYZmWwLCHVxdIIp4FMoe2FDaqQ")
    # APP_ID = os.environ.get("MicrosoftAppId", "")
    # APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")
