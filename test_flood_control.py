#!/usr/bin/env python3
"""
Test script for IRC flood control implementation
This script simulates rapid message sending to verify flood control works
"""

import time
import threading
from collections import deque
from flood_control_config import get_flood_control_config

class MockIRCConnection:
    """Mock IRC connection for testing"""
    def __init__(self):
        self.sent_messages = []
        self.send_times = []
    
    def privmsg(self, channel, message):
        """Mock privmsg method"""
        current_time = time.time()
        self.sent_messages.append(message)
        self.send_times.append(current_time)
        print(f"[{current_time:.3f}] SENT: {message}")
    
    def notice(self, target, message):
        """Mock notice method"""
        current_time = time.time()
        self.sent_messages.append(f"NOTICE {target}: {message}")
        self.send_times.append(current_time)
        print(f"[{current_time:.3f}] NOTICE {target}: {message}")

class FloodControlTester:
    """Test implementation of flood control logic"""
    
    def __init__(self, profile="default"):
        self.connection = MockIRCConnection()
        self.running = True
        
        # Load flood control configuration
        flood_config = get_flood_control_config(profile)
        
        # Flood control settings
        self.message_queue = deque()
        self.queue_lock = threading.Lock()
        self.last_message_time = 0
        self.message_interval = flood_config["message_interval"]
        self.burst_limit = flood_config["burst_limit"]
        self.burst_window = flood_config["burst_window"]
        self.min_message_delay = flood_config["min_message_delay"]
        self.chunk_delay = flood_config["chunk_delay"]
        self.burst_count = 0
        self.burst_reset_time = 0
        self.queue_processor_running = False
        
        print(f"Testing with profile: {profile}")
        print(f"Settings: interval={self.message_interval}s, burst_limit={self.burst_limit}, window={self.burst_window}s")
        print("-" * 60)
    
    def queue_message(self, message, is_notice=False, target=None):
        """Queue a message for rate-limited sending"""
        with self.queue_lock:
            message_data = {
                'message': message,
                'is_notice': is_notice,
                'target': target,
                'timestamp': time.time()
            }
            self.message_queue.append(message_data)
            
            # Start queue processor if not running
            if not self.queue_processor_running:
                self.queue_processor_running = True
                processor_thread = threading.Thread(target=self.process_message_queue, daemon=True)
                processor_thread.start()
    
    def process_message_queue(self):
        """Process queued messages with rate limiting"""
        while self.running:
            try:
                with self.queue_lock:
                    if not self.message_queue:
                        self.queue_processor_running = False
                        break
                    
                    message_data = self.message_queue.popleft()
                
                current_time = time.time()
                
                # Reset burst counter if window has passed
                if current_time - self.burst_reset_time > self.burst_window:
                    self.burst_count = 0
                    self.burst_reset_time = current_time
                
                # Calculate delay needed
                time_since_last = current_time - self.last_message_time
                delay_needed = 0
                
                if self.burst_count >= self.burst_limit:
                    # We've hit burst limit, enforce minimum interval
                    if time_since_last < self.message_interval:
                        delay_needed = self.message_interval - time_since_last
                elif time_since_last < self.min_message_delay:
                    delay_needed = self.min_message_delay - time_since_last
                
                if delay_needed > 0:
                    print(f"[{current_time:.3f}] DELAY: {delay_needed:.3f}s (burst_count={self.burst_count})")
                    time.sleep(delay_needed)
                
                # Send the message
                self.send_message_now(message_data)
                
                # Update counters
                self.last_message_time = time.time()
                self.burst_count += 1
                
            except Exception as e:
                print(f"Error in message queue processor: {e}")
                time.sleep(1)
    
    def send_message_now(self, message_data):
        """Actually send the message"""
        message = message_data['message']
        is_notice = message_data['is_notice']
        target = message_data['target']
        
        if is_notice and target:
            self.connection.notice(target, message)
        else:
            self.connection.privmsg("#test", message)
    
    def stop(self):
        """Stop the flood control system"""
        self.running = False
        time.sleep(0.1)  # Give processor thread time to finish

def test_burst_behavior(profile="default"):
    """Test burst behavior with rapid messages"""
    print(f"\n=== Testing Burst Behavior ({profile}) ===")
    
    tester = FloodControlTester(profile)
    start_time = time.time()
    
    # Send 6 messages rapidly
    messages = [
        "Message 1 - should be immediate",
        "Message 2 - should be immediate", 
        "Message 3 - should be immediate",
        "Message 4 - should be delayed",
        "Message 5 - should be delayed",
        "Message 6 - should be delayed"
    ]
    
    for i, msg in enumerate(messages):
        tester.queue_message(msg)
        if i < 3:
            time.sleep(0.05)  # Very small delay to simulate rapid sending
    
    # Wait for all messages to be processed
    time.sleep(8)
    tester.stop()
    
    # Analyze timing
    if len(tester.connection.send_times) > 1:
        intervals = []
        for i in range(1, len(tester.connection.send_times)):
            interval = tester.connection.send_times[i] - tester.connection.send_times[i-1]
            intervals.append(interval)
        
        print(f"\nTiming Analysis:")
        print(f"Total messages sent: {len(tester.connection.sent_messages)}")
        print(f"Message intervals: {[f'{x:.3f}s' for x in intervals]}")
        print(f"Total time: {tester.connection.send_times[-1] - start_time:.3f}s")

def test_notice_messages():
    """Test notice message handling"""
    print(f"\n=== Testing Notice Messages ===")
    
    tester = FloodControlTester("default")
    
    # Send some notices
    tester.queue_message("Private notice 1", is_notice=True, target="user1")
    tester.queue_message("Private notice 2", is_notice=True, target="user2")
    tester.queue_message("Channel message")
    tester.queue_message("Private notice 3", is_notice=True, target="user3")
    
    time.sleep(5)
    tester.stop()

def main():
    """Run all tests"""
    print("IRC Flood Control Test Suite")
    print("=" * 60)
    
    # Test different profiles
    for profile in ["default", "conservative", "aggressive"]:
        test_burst_behavior(profile)
    
    # Test notice messages
    test_notice_messages()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("\nTo use in your bot, add to IRC settings:")
    print('  flood_control_profile: "default"  # or "conservative" or "aggressive"')

if __name__ == "__main__":
    main()
