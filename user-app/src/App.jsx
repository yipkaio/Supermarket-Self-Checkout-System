import { useState } from "react";
import "./App.css";

const API_URL = "http://localhost:5000";

export default function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [userId, setUserId] = useState(null);
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");

  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState([]);
  const [showCart, setShowCart] = useState(false);

  const [toast, setToast] = useState("");

  const [showCheckoutModal, setShowCheckoutModal] = useState(false);

  const [showQR, setShowQR] = useState(false); // PayNow QR
  const [showPickupQR, setShowPickupQR] = useState(false); // Pickup QR

  const [qrImage, setQrImage] = useState("");
  const [qrValue, setQrValue] = useState("");

  const [deliveryType, setDeliveryType] = useState("pickup");
  const [paymentMethod] = useState("paynow");

  const [doneDisabled, setDoneDisabled] = useState(false); // prevent multi-click

  // ---------------- LOGIN ----------------
  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");

    try {
      const res = await fetch(`${API_URL}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(loginForm),
      });

      const data = await res.json();

      if (res.ok) {
        setLoggedIn(true);
        setUserId(data.user_id);
        fetchProducts();
      } else {
        setError(data.message || "Login failed");
      }
    } catch {
      setError("Backend not running");
    }
  };

  // ---------------- PRODUCTS ----------------
  const fetchProducts = async () => {
    const res = await fetch(`${API_URL}/products`);
    const data = await res.json();
    setProducts(data);
  };

  // ---------------- CART ----------------
  const addToCart = (product) => {
    setCart((prev) => {
      const found = prev.find((p) => p.product_id === product.product_id);
      if (found) {
        return prev.map((p) =>
          p.product_id === product.product_id ? { ...p, qty: p.qty + 1 } : p,
        );
      }
      return [...prev, { ...product, qty: 1 }];
    });

    setToast(`${product.name} added to cart`);
    setTimeout(() => setToast(""), 3000);
  };

  const removeFromCart = (id) => {
    setCart(cart.filter((item) => item.product_id !== id));
  };

  // ---------------- CHECKOUT ----------------
  const checkout = async () => {
    const items = cart.map((item) => ({
      product_id: item.product_id,
      quantity: item.qty,
    }));

    const res = await fetch(`${API_URL}/checkout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: userId,
        items,
        delivery_type: deliveryType,
        payment_method: paymentMethod,
      }),
    });

    if (res.ok) {
      setShowCheckoutModal(false);
      setShowQR(true); // show PayNow QR
      setDoneDisabled(false);
    }
  };

  // ---------------- LOGIN PAGE ----------------
  if (!loggedIn) {
    return (
      <div className="login-page">
        <form className="login-box" onSubmit={handleLogin}>
          <h2>Online Supermarket</h2>

          <input
            placeholder="Username"
            onChange={(e) =>
              setLoginForm({ ...loginForm, username: e.target.value })
            }
          />

          <input
            type="password"
            placeholder="Password"
            onChange={(e) =>
              setLoginForm({ ...loginForm, password: e.target.value })
            }
          />

          <button type="submit">Login</button>
          {error && <p className="error">{error}</p>}
        </form>
      </div>
    );
  }

  // ---------------- CART PAGE ----------------
  if (showCart) {
    return (
      <div className="page">
        <header className="header">
          <h2>🛒 Your Cart</h2>
          <button onClick={() => setShowCart(false)}>Back</button>
        </header>

        <div className="cart-page-container">
          {cart.length === 0 && (
            <p className="empty-cart">Your cart is empty</p>
          )}

          {cart.map((item) => (
            <div key={item.product_id} className="cart-row">
              <div className="cart-info">
                <h4 className="cart-name">{item.name}</h4>
                <p className="cart-qty">Qty: {item.qty}</p>
              </div>

              <div className="cart-price">
                <p>${(item.price * item.qty).toFixed(2)}</p>
              </div>

              <div className="cart-actions">
                <button
                  className="remove-btn"
                  onClick={() => removeFromCart(item.product_id)}
                >
                  Remove
                </button>
              </div>
            </div>
          ))}

          {cart.length > 0 && (
            <div className="cart-footer">
              <button
                className="checkout-btn"
                onClick={() => setShowCheckoutModal(true)}
              >
                Checkout
              </button>
            </div>
          )}
        </div>

        {/* ---------------- CHECKOUT MODAL ---------------- */}
        {showCheckoutModal && (
          <div className="modal-overlay">
            <div className="modal-box">
              <h2>Checkout</h2>

              <div className="section">
                <p>
                  <strong>Items Total:</strong> $
                  {cart.reduce((sum, i) => sum + i.price * i.qty, 0).toFixed(2)}
                </p>

                {deliveryType === "delivery" && (
                  <p className="delivery-fee">Delivery Fee: +$3.00</p>
                )}

                <p className="final-total">
                  <strong>Final Total:</strong> $
                  {(
                    cart.reduce((sum, i) => sum + i.price * i.qty, 0) +
                    (deliveryType === "delivery" ? 3 : 0)
                  ).toFixed(2)}
                </p>
              </div>

              <div className="section">
                <h4>Delivery Method</h4>

                <label>
                  <input
                    type="radio"
                    name="delivery"
                    checked={deliveryType === "pickup"}
                    onChange={() => setDeliveryType("pickup")}
                  />
                  In-store Pickup (Free)
                </label>

                <label>
                  <input
                    type="radio"
                    name="delivery"
                    checked={deliveryType === "delivery"}
                    onChange={() => setDeliveryType("delivery")}
                  />
                  Delivery (+$3)
                </label>
              </div>

              <div className="section">
                <h4>Payment Method</h4>
                <label>
                  <input type="radio" checked readOnly />
                  PayNow
                </label>
              </div>

              <div className="modal-actions">
                <button
                  className="cancel-btn"
                  onClick={() => setShowCheckoutModal(false)}
                >
                  Cancel
                </button>

                <button className="confirm-btn" onClick={checkout}>
                  Confirm Checkout
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ---------------- PAYNOW QR ---------------- */}
        {showQR && (
          <div className="modal-overlay">
            <div className="modal-box">
              <h2>Scan to Pay (PayNow)</h2>

              <img
                src="/Paynow.png"
                alt="PayNow QR"
                style={{
                  width: "220px",
                  display: "block",
                  margin: "20px auto",
                }}
              />

              <p style={{ textAlign: "center" }}>
                Please scan this QR code to complete payment
              </p>

              <button
                className="confirm-btn"
                disabled={doneDisabled}
                onClick={async () => {
                  if (doneDisabled) return;
                  setDoneDisabled(true);

                  // DELIVERY → no DB, no QR
                  if (deliveryType === "delivery") {
                    setShowQR(false);
                    setCart([]);
                    setShowCart(false);
                    fetchProducts();
                    return;
                  }

                  // PICKUP → create QR + save DB
                  const pickupItems = cart.map((item) => ({
                    product_id: item.product_id,
                    product_name: item.name,
                    quantity: item.qty,
                  }));

                  const res = await fetch(`${API_URL}/create-pickup`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      username: loginForm.username,
                      items: pickupItems,
                    }),
                  });

                  const data = await res.json();

                  console.log("Pickup response:", data);

                  if (!res.ok) {
                    alert("Pickup creation failed");
                    console.error(data);
                    return;
                  }

                  if (!data.qr_image || !data.qr_code) {
                    console.error("Missing QR data:", data);
                    alert("QR generation error");
                    return;
                  }

                  setShowQR(false);

                  const fullQrUrl = `${API_URL}${data.qr_image}`;
                  console.log("Full QR URL:", fullQrUrl);

                  console.log("FULL QR URL:", fullQrUrl);
                  console.log("QR CODE:", data.qr_code);

                  setQrImage(fullQrUrl);
                  setQrValue(data.qr_code);
                  setShowPickupQR(true);

                  setCart([]);
                  fetchProducts();
                }}
              >
                Done
              </button>
            </div>
          </div>
        )}

        {/* ---------------- PICKUP QR SCREEN ---------------- */}
        {showPickupQR && (
          <div className="modal-overlay">
            <div className="modal-box">
              <h2>Pickup Code</h2>

              <p style={{ textAlign: "center", fontWeight: "bold" }}>
                {qrValue}
              </p>

              <img
                src={qrImage}
                alt="Pickup QR"
                style={{
                  width: "260px",
                  display: "block",
                  margin: "20px auto",
                }}
              />

              <p style={{ textAlign: "center" }}>
                Show this QR at the pickup counter
              </p>

              <button
                className="confirm-btn"
                onClick={() => {setShowPickupQR(false);
                  setShowCart(false);
                }}
              >
                Finish
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ---------------- SHOP PAGE ----------------
  return (
    <div className="page">
      <header className="header">
        <h2>Online Supermarket</h2>
        <button onClick={() => setShowCart(true)}>Cart ({cart.length})</button>
      </header>

      <div className="container">
        <div className="grid">
          {products.map((p) => (
            <div key={p.product_id} className="card">
              <div className="img-box">
                <img
                  src={`${API_URL}/images/${p.image}`}
                  alt={p.name}
                  onError={(e) => {
                    e.target.src = "/no-image.png";
                  }}
                />
              </div>

              <h3 className="product-title">{p.name}</h3>
              <p className="price">${p.price}</p>
              <p className="stock">Stock: {p.stock}</p>

              <button onClick={() => addToCart(p)}>Add to Cart</button>
            </div>
          ))}
        </div>
      </div>

      {toast && <div className="snackbar">🛒 {toast}</div>}
    </div>
  );
}
