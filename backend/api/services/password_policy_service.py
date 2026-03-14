"""
Password Policy Service

This service handles password validation and hashing with enterprise-grade
security using Argon2 for password hashing and comprehensive validation rules.
"""
import re
import argon2
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from typing import List


class PasswordPolicyService:
    """Service for password validation and hashing with Argon2."""
    
    def __init__(self):
        """
        Initialize PasswordPolicyService with enterprise-grade Argon2 settings.
        """
        self.ph = PasswordHasher(
            memory_cost=65536,  # 64 MB
            time_cost=3,
            parallelism=4,
            hash_len=32,
            salt_len=16
        )
        
        # Common passwords list (commonly used in breaches)
        self.common_passwords = {
            'password', '123456', '123456789', 'qwerty', 'abc123', 'password123',
            'admin', 'letmein', 'welcome', 'monkey', 'dragon', 'master',
            'hello', 'login', 'princess', 'solo', 'starwars', 'trustno1',
            'passw0rd', 'password1', '12345678', 'football', 'iloveyou',
            'admin123', 'root', 'test', 'guest', 'user'
        }
    
    def validate_password(self, password: str) -> List[str]:
        """
        Validate password strength according to enterprise policy.
        
        Args:
            password: Password to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Length check
        if len(password) < 12:
            errors.append("Password must be at least 12 characters long")
        
        # Character type checks
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Common password check
        if password.lower() in self.common_passwords:
            errors.append("Password is too common and easily guessable")
        
        # Sequential character check (basic)
        if self._has_sequential_chars(password):
            errors.append("Password should not contain sequential characters")
        
        # Repeated character check
        if self._has_repeated_chars(password):
            errors.append("Password should not contain repeated characters")
        
        return errors
    
    def hash_password(self, password: str) -> str:
        """
        Hash password using Argon2 with enterprise settings.
        
        Args:
            password: Plain text password
            
        Returns:
            Argon2 hash string
        """
        return self.ph.hash(password)
    
    def verify_password(self, password: str, hash: str) -> bool:
        """
        Verify password against Argon2 hash.
        
        Args:
            password: Plain text password
            hash: Argon2 hash to verify against
            
        Returns:
            True if password matches hash, False otherwise
        """
        try:
            return self.ph.verify(hash, password)
        except VerifyMismatchError:
            return False
        except Exception:
            return False
    
    def needs_rehash(self, hash: str) -> bool:
        """
        Check if password hash needs to be rehashed with current parameters.
        
        Args:
            hash: Argon2 hash to check
            
        Returns:
            True if rehash is needed, False otherwise
        """
        try:
            return self.ph.check_needs_rehash(hash)
        except Exception:
            return True  # Rehash if we can't determine
    
    def get_password_strength_score(self, password: str) -> int:
        """
        Calculate password strength score (0-100).
        
        Args:
            password: Password to score
            
        Returns:
            Strength score from 0 to 100
        """
        score = 0
        
        # Base length score
        if len(password) >= 12:
            score += 20
        elif len(password) >= 8:
            score += 10
        
        # Character diversity
        if re.search(r'[A-Z]', password):
            score += 15
        if re.search(r'[a-z]', password):
            score += 15
        if re.search(r'\d', password):
            score += 15
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 20
        
        # Bonus for length
        if len(password) >= 16:
            score += 10
        elif len(password) >= 14:
            score += 5
        
        # Penalty for common patterns
        if password.lower() in self.common_passwords:
            score -= 30
        
        if self._has_sequential_chars(password):
            score -= 10
        
        if self._has_repeated_chars(password):
            score -= 10
        
        return max(0, min(100, score))
    
    def is_password_acceptable(self, password: str) -> bool:
        """
        Check if password meets minimum acceptable criteria.
        
        Args:
            password: Password to check
            
        Returns:
            True if password is acceptable, False otherwise
        """
        errors = self.validate_password(password)
        return len(errors) == 0
    
    def _has_sequential_chars(self, password: str) -> bool:
        """
        Check for sequential characters (basic implementation).
        
        Args:
            password: Password to check
            
        Returns:
            True if sequential chars found, False otherwise
        """
        password_lower = password.lower()
        
        # Check for sequential letters
        for i in range(len(password_lower) - 2):
            if (ord(password_lower[i+1]) == ord(password_lower[i]) + 1 and
                ord(password_lower[i+2]) == ord(password_lower[i]) + 2):
                return True
        
        # Check for sequential numbers
        for i in range(len(password) - 2):
            if (password[i+1] == str(int(password[i]) + 1) and
                password[i+2] == str(int(password[i]) + 2)):
                return True
        
        return False
    
    def _has_repeated_chars(self, password: str) -> bool:
        """
        Check for repeated characters.
        
        Args:
            password: Password to check
            
        Returns:
            True if repeated chars found, False otherwise
        """
        # Check for 3 or more consecutive identical characters
        for i in range(len(password) - 2):
            if password[i] == password[i+1] == password[i+2]:
                return True
        
        return False
    
    def get_password_policy_description(self) -> dict:
        """
        Get password policy description for UI display.
        
        Returns:
            Dictionary with policy requirements
        """
        return {
            "minimum_length": 12,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_numbers": True,
            "require_special_chars": True,
            "forbid_common_passwords": True,
            "forbid_sequential_chars": True,
            "forbid_repeated_chars": True,
            "hash_algorithm": "Argon2id",
            "memory_cost": "64 MB",
            "time_cost": 3,
            "parallelism": 4
        }