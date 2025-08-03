# IRC Flood Control Implementation

This document describes the flood control system implemented to prevent the IRC bot from being kicked due to flooding when bridging messages from Discord and Matrix.

## Problem

When multiple messages are sent quickly in Discord or Matrix, they all get bridged to IRC immediately without any rate limiting. This can cause the IRC server's flood protection to kick the bot.

## Solution

A comprehensive flood control system has been implemented with the following features:

### 1. Message Queuing System
- All IRC messages are now queued instead of sent immediately
- A background thread processes the queue with appropriate delays
- Thread-safe implementation using locks and deques

### 2. Rate Limiting Algorithm
The system implements a burst-aware rate limiting algorithm:

- **Burst Allowance**: Allows a configurable number of messages (default: 3) to be sent quickly
- **Burst Window**: Resets the burst counter every N seconds (default: 5s)
- **Message Interval**: After burst limit is reached, enforces minimum delay between messages (default: 1s)
- **Minimum Delay**: Always enforces a minimum delay between any messages (default: 0.2s)

### 3. Configurable Profiles

Three pre-configured profiles are available in `flood_control_config.py`:

#### Default Profile
```python
{
    "message_interval": 1.0,     # 1 second between messages after burst
    "burst_limit": 3,            # Allow 3 quick messages
    "burst_window": 5.0,         # Reset burst counter every 5 seconds
    "min_message_delay": 0.2,    # 200ms minimum between any messages
    "chunk_delay": 0.5           # 500ms between long message chunks
}
```

#### Conservative Profile (for strict IRC servers)
```python
{
    "message_interval": 2.0,     # 2 seconds between messages
    "burst_limit": 2,            # Allow only 2 quick messages
    "burst_window": 10.0,        # Longer reset window
    "min_message_delay": 0.5,    # 500ms minimum delay
    "chunk_delay": 1.0           # 1 second between chunks
}
```

#### Aggressive Profile (for lenient IRC servers)
```python
{
    "message_interval": 0.5,     # 500ms between messages
    "burst_limit": 5,            # Allow 5 quick messages
    "burst_window": 3.0,         # Shorter reset window
    "min_message_delay": 0.1,    # 100ms minimum delay
    "chunk_delay": 0.3           # 300ms between chunks
}
```

## Configuration

To configure flood control, add the following to your IRC settings in the configuration file:

```yaml
irc:
  # ... other IRC settings ...
  flood_control_profile: "default"  # or "conservative" or "aggressive"
```

If no profile is specified, "default" will be used.

## How It Works

### Message Flow
1. When a message needs to be sent to IRC, it's added to a queue
2. A background thread processes the queue continuously
3. Before sending each message, the system calculates if a delay is needed
4. Messages are sent with appropriate delays to respect IRC flood limits

### Rate Limiting Logic
```
For each message:
1. Check if burst window has expired → reset burst counter if needed
2. Calculate time since last message
3. If burst limit exceeded:
   - Enforce message_interval delay
4. Else:
   - Enforce min_message_delay
5. Sleep for calculated delay
6. Send message
7. Update counters
```

### Long Message Handling
- Messages longer than 400 characters are split into chunks
- Each chunk is sent with a configurable delay between them
- This prevents overwhelming the IRC server with large messages

## Benefits

1. **Prevents Bot Kicks**: Eliminates flooding-related disconnections
2. **Maintains Responsiveness**: Allows quick bursts of messages when needed
3. **Configurable**: Easy to adjust for different IRC server policies
4. **Transparent**: Existing code continues to work without changes
5. **Thread-Safe**: Handles concurrent message requests safely

## Monitoring

The system logs flood control activity:
- Profile selection and settings on startup
- Error handling in the message queue processor
- Debug information about delays and rate limiting

## Troubleshooting

### Bot Still Getting Kicked
- Try the "conservative" profile
- Check IRC server's specific flood limits
- Consider creating a custom profile with stricter settings

### Messages Delayed Too Much
- Try the "aggressive" profile
- Reduce the `message_interval` and `min_message_delay` values
- Increase the `burst_limit`

### Custom Configuration
You can create custom profiles by modifying `flood_control_config.py` or by directly setting flood control parameters in the IRC settings.

## Technical Details

### Files Modified
- `ircconnection.py`: Main flood control implementation
- `flood_control_config.py`: Configuration profiles (new file)

### Key Classes and Methods
- `IrcConnector.__queue_message()`: Adds messages to queue
- `IrcConnector.__process_message_queue()`: Background thread processing
- `IrcConnector.__send_message_now()`: Actual IRC message sending
- `get_flood_control_config()`: Configuration loader

### Thread Safety
- Uses `threading.Lock()` for queue access
- Daemon threads that terminate with main process
- Proper error handling to prevent thread crashes
