"""AWS service helper functions."""

import base64
import json
import logging
from typing import Dict, Optional

import boto3
import requests

logger = logging.getLogger(__name__)

# Initialize AWS clients
ssm_client = boto3.client("ssm")
cognito_client = boto3.client("cognito-idp")
sts_client = boto3.client("sts")


def get_ssm_parameter(parameter_name: str, with_decryption: bool = False) -> Optional[str]:
    """
    Get a parameter from AWS Systems Manager Parameter Store.

    Args:
        parameter_name: The name of the parameter
        with_decryption: Whether to decrypt secure strings

    Returns:
        The parameter value or None if not found
    """
    try:
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=with_decryption)
        return response["Parameter"]["Value"]
    except ssm_client.exceptions.ParameterNotFound:
        logger.warning("Parameter %s not found", parameter_name)
        return None
    except Exception as e:
        logger.error("Error getting parameter %s: %s", parameter_name, e)
        raise


def put_ssm_parameter(
    parameter_name: str, parameter_value: str, parameter_type: str = "String", overwrite: bool = True
) -> None:
    """
    Put a parameter in AWS Systems Manager Parameter Store.

    Args:
        parameter_name: The name of the parameter
        parameter_value: The value to store
        parameter_type: The type of parameter (String, StringList, or SecureString)
        overwrite: Whether to overwrite existing parameter
    """
    try:
        ssm_client.put_parameter(
            Name=parameter_name, Value=parameter_value, Type=parameter_type, Overwrite=overwrite
        )
        logger.info("Parameter %s stored successfully", parameter_name)
    except Exception as e:
        logger.error("Error storing parameter %s: %s", parameter_name, e)
        raise


def get_or_create_cognito_pool(refresh_token: bool = False) -> Dict[str, str]:
    """
    Get Cognito user pool configuration for Gateway authentication using OAuth2 client_credentials.

    Args:
        refresh_token: Whether to refresh the bearer token

    Returns:
        Dictionary containing:
        - client_id: The Cognito app client ID
        - discovery_url: The OIDC discovery URL
        - bearer_token: The authentication token (if refresh_token=True)
    """
    try:
        # Get configuration from SSM
        client_id = get_ssm_parameter("/app/customersupport/agentcore/machine_client_id")
        discovery_url = get_ssm_parameter("/app/customersupport/agentcore/cognito_discovery_url")

        config = {
            "client_id": client_id,
            "discovery_url": discovery_url,
        }

        if refresh_token:
            # Get OAuth2 client credentials
            client_secret = get_ssm_parameter("/app/customersupport/agentcore/machine_client_secret", with_decryption=True)
            token_url = get_ssm_parameter("/app/customersupport/agentcore/cognito_token_url")
            auth_scope = get_ssm_parameter("/app/customersupport/agentcore/cognito_auth_scope")

            # Use OAuth2 client_credentials flow
            auth_string = f"{client_id}:{client_secret}"
            auth_bytes = auth_string.encode('utf-8')
            auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')

            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            data = {
                "grant_type": "client_credentials",
                "scope": auth_scope
            }

            response = requests.post(token_url, headers=headers, data=data, timeout=10)
            response.raise_for_status()

            token_response = response.json()
            config["bearer_token"] = token_response["access_token"]
            config["access_token"] = token_response["access_token"]
            config["token_type"] = token_response.get("token_type", "Bearer")

        return config

    except Exception as e:
        logger.error("Error getting/creating Cognito pool: %s", e)
        raise ValueError(
            "Cognito configuration not found or invalid. "
            "Please ensure the workshop prerequisites are set up correctly."
        ) from e


def get_aws_account_id() -> str:
    """Get the current AWS account ID."""
    return sts_client.get_caller_identity()["Account"]


def get_aws_region() -> str:
    """Get the current AWS region."""
    session = boto3.session.Session()
    return session.region_name


def load_api_spec(file_path: str) -> list:
    """
    Load API specification from a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        The parsed API specification
    """
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("API spec file not found: %s", file_path)
        raise
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in API spec file: %s", e)
        raise
