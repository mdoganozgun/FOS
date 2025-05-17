# FOS
The Online Food Ordering System (FOs) is a database-driven web application developed as a part of the CS202: Database Management Systems course at Özyeğin University, Spring 2025 semester.

This project simulates a real-world food delivery platform similar to Yemeksepeti, GetirYemek, Uber Eats, or DoorDash, with a focus on core database design, SQL integration, and backend web development using Python and Flask.

The system supports two main user types:
	•	Customers: who can register, search restaurants based on keywords and city, place orders, and rate their experiences.
	•	Restaurant Managers: who can define menus, apply time-limited discounts, manually accept orders, and track sales statistics such as revenue, best-selling items, and customer order behavior.

Although the payment and delivery logistics are outside the system’s scope, the project tracks their statuses:
	•	Payment: method (cash or credit card) and status (pending or paid)
	•	Delivery: status (not started, out for delivery, delivered)

The backend is built using Flask (Python) with MySQL as the database. All SQL queries are manually written using MySQL Connector/Python, as per the course constraints (ORMs are not allowed). The frontend is implemented using HTML/CSS/JS with Jinja2 templates for dynamic rendering.

This project emphasizes strong database normalization, proper entity-relationship modeling, referential integrity, and modular backend logic—offering hands-on experience with building a scalable and practical web-based system.
