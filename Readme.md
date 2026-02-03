# Group 3 AIoT DevOps Mini Project: Supermarket Self-Checkout System 

## 1. Project Overview
The **Supermarket Self-Checkout System** is an automated checkout solution designed for SPmart Supermarket to reduce customer waiting time during payment.  
The system supports both **in-store self-checkout** and **online purchases**, providing a seamless and efficient shopping experience.

Customers can:
- Scan products and pay independently in-store
- Purchase items online via a mobile app or website
- Choose between **store pickup** or **home delivery**
- Pay using multiple payment modes

---

## 2. Objectives
- Reduce checkout queue time
- Improve customer convenience
- Support multiple purchasing methods (online & in-store)
- Provide secure and flexible payment options
- Maintain accurate and centralized product data

---

## 3. System Scope
### In Scope
- Barcode scanning using camera
- Product lookup from central database
- Real-time display of item details and total cost
- ATM PIN and RFID (PayWave) payments
- Online ordering with QR code generation
- Store pickup and home delivery options

### Out of Scope
- Inventory supplier management
- Employee payroll systems
- External banking systems (assumed to exist)

---

## 4. System Requirements

### 4.1 Functional Requirements

#### In-Store Purchases
- Each product has a **10-digit unique barcode**
- Camera scans product barcode
- System retrieves product details from database
- LCD displays:
  - Product name
  - Product price
  - Cumulative total
- Supports multiple item scans per transaction

#### Online Purchases
- Customers can purchase via:
  - Smartphone App
  - Web Application
- Customers can choose:
  - Store pickup
  - Home delivery (additional $4.00 fee)
- QR code generated after successful online payment
- QR code is used for item collection at supermarket

#### Payment Modes
- ATM payment via numeric keypad (PIN-based)
- PayWave payment via RFID card reader

---

### 4.2 Non-Functional Requirements
- Fast response time (< 2 seconds per scan)
- High availability during operating hours
- Secure handling of payment and customer data
- User-friendly interface
- Scalable for future features (e.g. loyalty points)

---

## 5. System Architecture

### 5.1 High-Level Architecture
The system follows a **client-server architecture** with centralized data management.


---

### 5.2 Software Components
- **Frontend**
  - In-store LCD UI
  - Web application
  - Mobile application
- **Backend**
  - Product management
  - Transaction handling
  - Payment processing
  - QR code generation
- **Database**
  - Product details
  - Prices
  - Orders
  - Transactions

---

## 6. UML Diagrams

### 6.1 Use Case Diagram (Description)
**Actors**
- Customer
- Supermarket Staff
- Payment System

**Main Use Cases**
- Scan product
- View total price
- Make payment
- Purchase online
- Generate QR code
- Collect items
- Deliver items

---

### 6.2 Class Diagram (Description)

**Main Classes**
- `Product`
  - productID
  - name
  - price
- `Transaction`
  - transactionID
  - totalAmount
  - paymentMethod
- `Customer`
  - customerID
  - purchaseType
- `Order`
  - orderID
  - deliveryMethod
  - qrCode
- `Payment`
  - paymentType
  - paymentStatus

---

### 6.3 Sequence Diagram (In-Store Purchase)


---

## 7. System Workflow

### In-Store Checkout
1. Customer scans product barcode
2. System retrieves product details
3. LCD displays product and total price
4. Customer selects payment method
5. Payment is processed
6. Receipt is generated

### Online Purchase
1. Customer browses products online
2. Items added to cart
3. Payment completed
4. QR code generated
5. Customer collects items or receives delivery

---

## 8. Technologies Used (Proposed)
- Frontend: HTML, CSS, JavaScript
- Backend: Python (Flask) / Node.js
- Database: MySQL
- Hardware:
  - Camera for barcode scanning
  - LCD display
  - Numeric keypad
  - RFID card reader

---

## 9. Installation & Setup (Future Work)
Instructions will be provided once implementation is completed.

---

## 10. Usage
- Launch in-store system for self-checkout
- Access web/mobile app for online purchases
- Follow on-screen instructions to complete checkout
- Present QR code for item collection if applicable

---

## 11. Future Enhancements
- Loyalty reward system
- Mobile wallet integration
- AI-based product recognition
- Receipt-less checkout
- Multi-language support

---

## 12. Authors
Developed as part of a mini-project for academic purposes.

---

## 13. License
This project is for educational use only.


