import io
import os
import sys


sys.path.insert(0, os.path.abspath("../.."))

import asyncio
import gzip
import json
import logging
import time
from unittest.mock import AsyncMock, patch

import pytest

import litellm
from litellm import completion
from litellm._logging import verbose_logger
from litellm.integrations.custom_guardrail import CustomGuardrail


from typing import Any, Dict, List, Literal, Optional, Union

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.caching.caching import DualCache
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.proxy._types import UserAPIKeyAuth
from litellm.proxy.guardrails.guardrail_helpers import should_proceed_based_on_metadata
from litellm.types.guardrails import GuardrailEventHooks


def test_get_guardrail_from_metadata():
    guardrail = CustomGuardrail(guardrail_name="test-guardrail")

    # Test with empty metadata
    assert guardrail.get_guardrail_from_metadata({}) == []

    # Test with guardrails in metadata
    data = {"metadata": {"guardrails": ["guardrail1", "guardrail2"]}}
    assert guardrail.get_guardrail_from_metadata(data) == ["guardrail1", "guardrail2"]

    # Test with dict guardrails
    data = {
        "metadata": {
            "guardrails": [{"test-guardrail": {"extra_body": {"key": "value"}}}]
        }
    }
    assert guardrail.get_guardrail_from_metadata(data) == [
        {"test-guardrail": {"extra_body": {"key": "value"}}}
    ]


def test_guardrail_is_in_requested_guardrails():
    guardrail = CustomGuardrail(guardrail_name="test-guardrail")

    # Test with string list
    assert (
        guardrail._guardrail_is_in_requested_guardrails(["test-guardrail", "other"])
        == True
    )
    assert guardrail._guardrail_is_in_requested_guardrails(["other"]) == False

    # Test with dict list
    assert (
        guardrail._guardrail_is_in_requested_guardrails(
            [{"test-guardrail": {"extra_body": {"extra_key": "extra_value"}}}]
        )
        == True
    )
    assert (
        guardrail._guardrail_is_in_requested_guardrails(
            [
                {
                    "other-guardrail": {"extra_body": {"extra_key": "extra_value"}},
                    "test-guardrail": {"extra_body": {"extra_key": "extra_value"}},
                }
            ]
        )
        == True
    )
    assert (
        guardrail._guardrail_is_in_requested_guardrails(
            [{"other-guardrail": {"extra_body": {"extra_key": "extra_value"}}}]
        )
        == False
    )


def test_should_run_guardrail():
    guardrail = CustomGuardrail(
        guardrail_name="test-guardrail", event_hook=GuardrailEventHooks.pre_call
    )

    # Test matching event hook and guardrail
    assert (
        guardrail.should_run_guardrail(
            {"metadata": {"guardrails": ["test-guardrail"]}},
            GuardrailEventHooks.pre_call,
        )
        == True
    )

    # Test non-matching event hook
    assert (
        guardrail.should_run_guardrail(
            {"metadata": {"guardrails": ["test-guardrail"]}},
            GuardrailEventHooks.during_call,
        )
        == False
    )

    # Test guardrail not in requested list
    assert (
        guardrail.should_run_guardrail(
            {"metadata": {"guardrails": ["other-guardrail"]}},
            GuardrailEventHooks.pre_call,
        )
        == False
    )


def test_get_guardrail_dynamic_request_body_params():
    guardrail = CustomGuardrail(guardrail_name="test-guardrail")

    # Test with no extra_body
    data = {"metadata": {"guardrails": [{"test-guardrail": {}}]}}
    assert guardrail.get_guardrail_dynamic_request_body_params(data) == {}

    # Test with extra_body
    data = {
        "metadata": {
            "guardrails": [{"test-guardrail": {"extra_body": {"key": "value"}}}]
        }
    }
    assert guardrail.get_guardrail_dynamic_request_body_params(data) == {"key": "value"}

    # Test with non-matching guardrail
    data = {
        "metadata": {
            "guardrails": [{"other-guardrail": {"extra_body": {"key": "value"}}}]
        }
    }
    assert guardrail.get_guardrail_dynamic_request_body_params(data) == {}
