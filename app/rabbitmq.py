import pika
import json
import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")

def publish_booking_confirmed(booking_id, user_id, event_id, event_name="Sample Event", user_email="user@example.com"):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        channel = connection.channel()
        
        # For Ticket-Generator
        channel.queue_declare(queue="payment_completed_queue", durable=True)
        channel.basic_publish(
            exchange="",
            routing_key="payment_completed_queue",
            body=json.dumps({
                "booking_id": str(booking_id), 
                "event_id": str(event_id), 
                "user_id": str(user_id)
            }),
            properties=pika.BasicProperties(delivery_mode=2) # make message persistent
        )
        
        # For notification-service
        channel.queue_declare(queue="notification_queue", durable=True)
        channel.basic_publish(
            exchange="",
            routing_key="notification_queue",
            body=json.dumps({
                "type": "payment.success", 
                "email": user_email, 
                "eventName": event_name,
                "booking_id": str(booking_id)
            }),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        print(f" [x] Published booking confirmation for ID: {booking_id}")
    except Exception as e:
        print(f" [!] Failed to publish to RabbitMQ: {e}")
