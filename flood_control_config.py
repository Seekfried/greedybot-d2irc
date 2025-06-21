"""
Flood control configuration for IRC bridge
Adjust these settings based on your IRC server's flood protection limits
"""

# Default flood control settings
DEFAULT_FLOOD_CONTROL = {
    # Minimum seconds between messages when burst limit is exceeded
    "message_interval": 1.0,
    
    # Allow up to N messages in quick succession before enforcing stricter limits
    "burst_limit": 3,
    
    # Reset burst counter every N seconds
    "burst_window": 5.0,
    
    # Minimum milliseconds between any messages (prevents rapid-fire)
    "min_message_delay": 0.2,
    
    # Delay between chunks when splitting long messages
    "chunk_delay": 0.5
}

# Conservative settings for strict IRC servers
CONSERVATIVE_FLOOD_CONTROL = {
    "message_interval": 2.0,
    "burst_limit": 2,
    "burst_window": 10.0,
    "min_message_delay": 0.5,
    "chunk_delay": 1.0
}

# Aggressive settings for lenient IRC servers
AGGRESSIVE_FLOOD_CONTROL = {
    "message_interval": 0.5,
    "burst_limit": 5,
    "burst_window": 3.0,
    "min_message_delay": 0.1,
    "chunk_delay": 0.3
}

def get_flood_control_config(profile="default"):
    """
    Get flood control configuration by profile name
    
    Args:
        profile (str): Configuration profile ("default", "conservative", "aggressive")
        
    Returns:
        dict: Flood control configuration
    """
    profiles = {
        "default": DEFAULT_FLOOD_CONTROL,
        "conservative": CONSERVATIVE_FLOOD_CONTROL,
        "aggressive": AGGRESSIVE_FLOOD_CONTROL
    }
    
    return profiles.get(profile, DEFAULT_FLOOD_CONTROL).copy()
