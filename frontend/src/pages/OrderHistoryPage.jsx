import "../styles/OrderHistory.css";

const MOCK_ORDERS = [];

export default function OrderHistoryPage() {
    return (
        <div className="inner-page">
            <div className="bg-orbs">
                <div className="orb orb-1" style={{ opacity: 0.07 }} />
            </div>

            <div className="inner-page-body">
                <div className="page-header">
                    <div className="page-eyebrow">Order History</div>
                    <h1 className="page-title">Your Orders</h1>
                    <p className="page-sub">View and manage your subscription and purchase history.</p>
                </div>

                <div className="panel oh-panel" style={{ animationDelay: "0.1s" }}>
                    {MOCK_ORDERS.length > 0 ? (
                        <table className="oh-table">
                            <thead>
                                <tr>
                                    <th>Order ID</th>
                                    <th>Plan</th>
                                    <th>Amount</th>
                                    <th>Date</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {MOCK_ORDERS.map(order => (
                                    <tr key={order.id}>
                                        <td className="oh-id">{order.id}</td>
                                        <td>{order.plan}</td>
                                        <td>{order.amount}</td>
                                        <td>{order.date}</td>
                                        <td>
                                            <span className={`oh-status oh-status--${order.status.toLowerCase()}`}>
                                                {order.status}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <div className="coming-soon-placeholder">
                            <div className="coming-soon-icon">🧾</div>
                            <div className="coming-soon-text">
                                No orders yet.<br />
                                Upgrade to a paid plan to see your billing history here.
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
