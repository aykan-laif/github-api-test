import os
import boto3
import requests
import argparse
from typing import Dict, Optional

class GitHubEnvironmentManager:
    def __init__(self, token: Optional[str] = None):
        """
        Initialize with either:
        - token passed directly
        - token from environment variable
        - token from AWS Parameter Store
        """
        self.token = token or self._get_token()
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def _get_token(self) -> str:
        """
        Try to get token in order of precedence:
        1. Environment variable
        2. AWS Parameter Store
        3. Raise error if not found
        """
        # Try environment variable
        if token := os.getenv('GITHUB_TOKEN'):
            return token

        # Try AWS Parameter Store
        try:
            ssm = boto3.client('ssm')
            response = ssm.get_parameter(
                Name='/github/api_token',
                WithDecryption=True
            )
            return response['Parameter']['Value']
        except Exception as e:
            print(f"Could not retrieve token from AWS: {e}")

        raise ValueError("No GitHub token found in environment or AWS")

    def test_connection(self) -> bool:
        """Test if the token works"""
        try:
            response = requests.get(
                f"{self.base_url}/user",
                headers=self.headers
            )
            if response.status_code == 200:
                print("✅ Successfully connected to GitHub API")
                return True
            else:
                print(f"❌ Failed to connect: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False

    def create_environment(self, repo_owner: str, repo_name: str, env_name: str) -> bool:
        """Create a GitHub environment"""
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/environments/{env_name}"
        
        try:
            response = requests.put(url, headers=self.headers)
            if response.status_code in [200, 201]:
                print(f"✅ Created environment: {env_name}")
                return True
            else:
                print(f"❌ Failed to create environment {env_name}: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error creating environment: {e}")
            return False

    def set_environment_variables(self, repo_owner: str, repo_name: str, 
                                env_name: str, variables: Dict[str, str]) -> bool:
        """Set environment variables"""
        for key, value in variables.items():
            url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/environments/{env_name}/variables"
            data = {
                "name": key,
                "value": value
            }
            
            try:
                response = requests.post(url, headers=self.headers, json=data)
                if response.status_code in [200, 201]:
                    print(f"✅ Set variable {key} in {env_name}")
                else:
                    print(f"❌ Failed to set {key}: {response.status_code}")
                    print(f"Response: {response.text}")
                    return False
            except Exception as e:
                print(f"❌ Error setting variable {key}: {e}")
                return False
        return True

def main():
    parser = argparse.ArgumentParser(description='Test GitHub Environment Setup')
    parser.add_argument('--token', help='GitHub token (optional)')
    parser.add_argument('--store-token', action='store_true', 
                       help='Store token in AWS Parameter Store')
    args = parser.parse_args()

    # Initialize manager
    manager = GitHubEnvironmentManager(token=args.token)

    # Test connection
    if not manager.test_connection():
        return

    # Test variables
    test_variables = {
        "TEST_VAR_1": "value1",
        "TEST_VAR_2": "value2",
    }

    # Test environment creation and variable setting
    repo_owner = "your-org"  # Replace with your org/username
    repo_name = "your-repo"  # Replace with your repo name
    
    if manager.create_environment(repo_owner, repo_name, "test"):
        manager.set_environment_variables(repo_owner, repo_name, "test", test_variables)

    # Optionally store token in AWS
    if args.store_token and args.token:
        try:
            ssm = boto3.client('ssm')
            ssm.put_parameter(
                Name='/github/api_token',
                Value=args.token,
                Type='SecureString',
                Overwrite=True
            )
            print("✅ Token stored in AWS Parameter Store")
        except Exception as e:
            print(f"❌ Failed to store token: {e}")

if __name__ == "__main__":
    main()