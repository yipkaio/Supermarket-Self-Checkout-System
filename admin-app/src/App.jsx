import { useState, useEffect } from "react";
import { LogIn, LogOut, Plus, Edit2, Trash2, RefreshCw } from "lucide-react";
import "./App.css";

const API_URL = "http://localhost:5000/api";

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [products, setProducts] = useState([]);
  const [editingProduct, setEditingProduct] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [loginError, setLoginError] = useState("");
  const [newProduct, setNewProduct] = useState({
    name: "",
    price: "",
    stock: "",
    image: null,
  });
  const [editForm, setEditForm] = useState({ price: "", stock: "" });

  useEffect(() => {
    if (isLoggedIn) fetchProducts();
  }, [isLoggedIn]);

  const showNotification = (text, type = "success") => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/products`);
      if (!response.ok) throw new Error("Failed to fetch products");
      const data = await response.json();
      setProducts(data);
    } catch {
      showNotification("Failed to load products", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setLoginError("");

    try {
      const response = await fetch(`${API_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(loginForm),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setIsLoggedIn(true);
        setLoginForm({ username: "", password: "" });
        showNotification(`Welcome, ${data.user.username}!`);
      } else {
        setLoginError(data.error || "Login failed");
      }
    } catch {
      setLoginError(
        "Cannot connect to server. Is backend running on port 5000?",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setProducts([]);
    setEditingProduct(null);
    setShowAddForm(false);
    showNotification("Logged out successfully");
  };

  const handleAddProduct = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("name", newProduct.name);
      formData.append("price", newProduct.price);
      formData.append("stock", newProduct.stock);
      if (newProduct.image) formData.append("image", newProduct.image);

      const response = await fetch(`${API_URL}/products`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (response.ok && data.success) {
        showNotification("✅ Product added to database!");
        await fetchProducts();
        setNewProduct({ name: "", price: "", stock: "", image: null });
        setShowAddForm(false);
      } else {
        showNotification(data.error || "Failed to add product", "error");
      }
    } catch {
      showNotification("Failed to add product", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProduct = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/products/${editingProduct.product_id}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(editForm),
        },
      );

      const data = await response.json();

      if (response.ok && data.success) {
        showNotification("✅ Product updated in database!");
        await fetchProducts();
        setEditingProduct(null);
        setEditForm({ price: "", stock: "" });
      } else {
        showNotification(data.error || "Failed to update product", "error");
      }
    } catch {
      showNotification("Failed to update product", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProduct = async (id, name) => {
    if (!window.confirm(`Delete "${name}"?`)) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/products/${id}`, {
        method: "DELETE",
      });

      const data = await response.json();

      if (response.ok && data.success) {
        showNotification("🗑️ Product deleted from database!");
        await fetchProducts();
      } else {
        showNotification(data.error || "Failed to delete product", "error");
      }
    } catch {
      showNotification("Failed to delete product", "error");
    } finally {
      setLoading(false);
    }
  };

  const startEdit = (product) => {
    setEditingProduct(product);
    setEditForm({ price: product.price, stock: product.stock });
  };

  /* ========== LOGIN PAGE ========== */
  if (!isLoggedIn) {
    return (
      <div className="login-page">
        <h1>🏪 Inventory System</h1>
        <p>Login to manage products</p>

        <form onSubmit={handleLogin}>
          <input
            type="text"
            placeholder="Username"
            value={loginForm.username}
            onChange={(e) =>
              setLoginForm({ ...loginForm, username: e.target.value })
            }
          />

          <input
            type="password"
            placeholder="Password"
            value={loginForm.password}
            onChange={(e) =>
              setLoginForm({ ...loginForm, password: e.target.value })
            }
          />

          <button type="submit">{loading ? "Logging in..." : "Login"}</button>
        </form>

        {loginError && <p className="error">{loginError}</p>}
        <p>💡 Default: admin / admin123</p>
      </div>
    );
  }

  /* ========== EDIT PAGE ========== */
  if (editingProduct) {
    return (
      <div className="edit-page">
        {message && <div className={`msg ${message.type}`}>{message.text}</div>}

        <h2>✏️ Edit Product</h2>
        <h3>{editingProduct.name}</h3>

        <form onSubmit={handleUpdateProduct}>
          <label>
            Price ($)
            <input
              type="number"
              step="0.01"
              value={editForm.price}
              onChange={(e) =>
                setEditForm({ ...editForm, price: e.target.value })
              }
            />
          </label>

          <label>
            Stock Quantity
            <input
              type="number"
              value={editForm.stock}
              onChange={(e) =>
                setEditForm({ ...editForm, stock: e.target.value })
              }
            />
          </label>

          <button type="submit">
            {loading ? "Saving..." : "Save Changes"}
          </button>

          <button
            type="button"
            className="btn-secondary"
            onClick={() => setEditingProduct(null)}
          >
            Cancel
          </button>
        </form>
      </div>
    );
  }

  /* ========== MAIN INVENTORY PAGE ========== */
  return (
    <div className="inventory-page">
      {message && <div className={`msg ${message.type}`}>{message.text}</div>}

      <header>
        <h1>📦 Company Inventory</h1>
        <p>{products.length} products in database</p>

        <button onClick={handleLogout}>
          <LogOut size={16} /> Logout
        </button>
      </header>

      {!showAddForm ? (
        <button className="btn-add" onClick={() => setShowAddForm(true)}>
          <Plus size={16} /> Add New Product
        </button>
      ) : (
        <form className="add-form" onSubmit={handleAddProduct}>
          <h2>➕ Add New Product</h2>

          <input
            type="text"
            placeholder="Product Name"
            value={newProduct.name}
            onChange={(e) =>
              setNewProduct({ ...newProduct, name: e.target.value })
            }
            required
          />

          <input
            type="number"
            step="0.01"
            placeholder="Price"
            value={newProduct.price}
            onChange={(e) =>
              setNewProduct({ ...newProduct, price: e.target.value })
            }
            required
          />

          <input
            type="number"
            placeholder="Stock Quantity"
            value={newProduct.stock}
            onChange={(e) =>
              setNewProduct({ ...newProduct, stock: e.target.value })
            }
            required
          />

          <input
            type="file"
            accept="image/*"
            onChange={(e) =>
              setNewProduct({ ...newProduct, image: e.target.files[0] })
            }
          />

          <button type="submit">
            {loading ? "Adding..." : "Add to Database"}
          </button>

          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              setShowAddForm(false);
              setNewProduct({ name: "", price: "", stock: "", image: null });
            }}
          >
            Cancel
          </button>
        </form>
      )}

      {loading && <p>⏳ Loading...</p>}

      <div className="product-grid">
        {products.map((product) => (
          <div key={product.product_id} className="product-card">
            <div
              className="product-img"
              style={{
                backgroundImage: product.image
                  ? `url(http://localhost:5000/static/images/uploads/${product.image})`
                  : "none",
              }}
            >
              {!product.image && "📦"}
            </div>

            <h3>{product.name}</h3>
            <p>${parseFloat(product.price).toFixed(2)}</p>
            <p>Stock: {product.stock}</p>

            <button onClick={() => startEdit(product)}>
              <Edit2 size={14} /> Edit
            </button>

            <button
              className="btn-delete"
              onClick={() =>
                handleDeleteProduct(product.product_id, product.name)
              }
            >
              <Trash2 size={14} /> Delete
            </button>
          </div>
        ))}
      </div>

      {products.length === 0 && !loading && (
        <div className="empty">
          <p>📭 No products in database</p>
          <p>Click "Add New Product" to get started</p>
        </div>
      )}
    </div>
  );
}

export default App;
