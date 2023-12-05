#!/bin/bash

CONTAINER_NAME="chain-monitoring"
MEMORY_THRESHOLD=10

# while true; do
#     MEMORY_USAGE=$(docker stats --no-stream --format "{{.MemPerc}}" "$CONTAINER_NAME" | awk -F'%' '{print $1}')
    
#     if (( $(echo "$MEMORY_USAGE > $MEMORY_THRESHOLD" | bc -l) )); then
#         echo "Memory usage of $CONTAINER_NAME is above $MEMORY_THRESHOLD%"
#         echo "Restarting container and clearing memory..."
        
#         docker restart "$CONTAINER_NAME"
#         # Additional commands to clear memory if applicable

#         sleep 5  # Wait before checking again (adjust as needed)
#     else
#         echo "Memory usage is below threshold: $MEMORY_USAGE%"
#         sleep 60  # Check memory usage every 60 seconds
#     fi
# done

MEMORY_USAGE=$(docker stats --no-stream --format "{{.MemPerc}}" "$CONTAINER_NAME" | awk -F'%' '{print $1}')
    
if (( $(echo "$MEMORY_USAGE > $MEMORY_THRESHOLD" | bc -l) )); then
    echo "Memory usage of $CONTAINER_NAME is above $MEMORY_THRESHOLD%"
    echo "Restarting container and clearing memory..."
    
    docker restart "$CONTAINER_NAME"
    # Additional commands to clear memory if applicable

    sleep 5  # Wait before checking again (adjust as needed)
else
    echo "Memory usage is below threshold: $MEMORY_USAGE%"
    sleep 60  # Check memory usage every 60 seconds
fi