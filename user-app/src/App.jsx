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
  const [purchaseToast, setPurchaseToast] = useState(false);
  const [purchaseTotal, setPurchaseTotal] = useState(0);

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

  const fetchProducts = async () => {
    const res = await fetch(`${API_URL}/products`);
    const data = await res.json();
    setProducts(data);
  };

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

    // snackbar
    setToast(`${product.name} added to cart`);
    setTimeout(() => setToast(""), 3000);
  };

  const removeFromCart = (id) => {
    setCart(cart.filter((item) => item.product_id !== id));
  };

  const checkout = async () => {
    const items = cart.map((item) => ({
      product_id: item.product_id,
      quantity: item.qty,
    }));

    const res = await fetch(`${API_URL}/checkout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, items }),
    });

    const data = await res.json();

    if (res.ok) {
      setPurchaseTotal(data.total);
      setPurchaseToast(true);

      setTimeout(() => {
        setPurchaseToast(false);
      }, 3000);

      setCart([]);
      setShowCart(false);
      fetchProducts();
    } else {
      alert(data.error);
    }
  };

  /* ================= LOGIN PAGE ================= */
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

  /* ================= CART PAGE ================= */
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
              <button className="checkout-btn" onClick={checkout}>
                Checkout
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  /* ================= MAIN SHOP PAGE ================= */
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

      {/* ADD TO CART SNACKBAR */}
      {toast && <div className="snackbar">🛒 {toast}</div>}

      {/* PURCHASE SNACKBAR */}
      {purchaseToast && (
        <div className="snackbar success">
          ✅ Purchase successful — Total: ${purchaseTotal}
        </div>
      )}
    </div>
  );
}
