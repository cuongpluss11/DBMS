// ============================================================================
// KỊCH BẢN KIỂM CHỨNG & DEMO CHỨC NĂNG CƠ BẢN MONGODB 8.0.20 (MỤC 1.4 & PHỤ LỤC A.8)
// Công cụ: MongoDB Compass (tab >_ MONGOSH) hoặc mongosh CLI
// Kết nối: mongodb://127.0.0.1:27018/?directConnection=true
// Chạy toàn bộ file từ CLI:
//   mongosh "mongodb://127.0.0.1:27018/?directConnection=true" scripts/demo/demo_mongo_1.4.js
// ============================================================================

print("=== [A.8 - Kịch bản 1] Kiểm chứng phiên bản & trạng thái Replica Set (Hình A.1) ===");
print("MongoDB version:", db.version());
printjson(
  rs.status().members.map(m => ({
    id: m._id,
    name: m.name,
    stateStr: m.stateStr,
    health: m.health
  }))
);

// ----------------------------------------------------------------------------
// [A.8 - Kịch bản 2] CRUD cơ bản trên mô hình Document BSON (demo_flashsale)
// ----------------------------------------------------------------------------
print("\n=== [A.8 - Kịch bản 2] CRUD cơ bản trên BSON ===");
db = db.getSiblingDB("demo_flashsale");
db.item.drop();
db.stock.drop();
db.orders.drop();

// CREATE: Chèn sản phẩm 101, tồn kho ban đầu = 5 và 1 đơn nháp kiểm thử xóa
printjson(db.item.insertOne({ i_id: 101, i_name: "Tai nghe Flash-Sale", i_price: 500000 }));
printjson(db.stock.insertOne({ s_w_id: 1, s_i_id: 101, s_quantity: 5 }));
printjson(db.orders.insertOne({ o_id: 9000, o_i_id: 101, qty: 1, status: "TEST_DELETE" }));

// READ: Truy vấn lại document BSON
print("Item 101:");
printjson(db.item.findOne({ i_id: 101 }));
print("Stock (1, 101):");
printjson(db.stock.findOne({ s_w_id: 1, s_i_id: 101 }));

// DELETE: Xóa sạch đơn nháp 9000, giữ nguyên tồn kho = 5 cho Kịch bản 3
printjson(db.orders.deleteOne({ o_id: 9000 }));
print("Orders sau khi xóa đơn nháp:", db.orders.countDocuments({}));

// ----------------------------------------------------------------------------
// [A.8 - Kịch bản 3] Cập nhật nguyên tử có điều kiện — Chống âm kho (Hình A.2)
// ----------------------------------------------------------------------------
print("\n=== [A.8 - Kịch bản 3] Cập nhật nguyên tử chống âm kho (Hình A.2) ===");

// (a) Mua 3 khi kho còn 5 -> đủ hàng (5 >= 3): modifiedCount = 1, tồn giảm còn 2
print("Lần (a) - Mua 3 khi còn 5:");
printjson(
  db.stock.updateOne(
    { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 3 } },
    { $inc: { s_quantity: -3 } }
  )
);

// (b) Mua 4 khi kho còn 2 -> thiếu hàng (2 < 4): modifiedCount = 0, từ chối cập nhật
print("Lần (b) - Mua 4 khi còn 2:");
printjson(
  db.stock.updateOne(
    { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 4 } },
    { $inc: { s_quantity: -4 } }
  )
);

print("Tồn kho sau 2 lần cập nhật (kỳ vọng s_quantity = 2):");
printjson(db.stock.findOne({ s_w_id: 1, s_i_id: 101 }));

// ----------------------------------------------------------------------------
// [A.8 - Kịch bản 4] Giao dịch ACID nhiều tài liệu — COMMIT & ABORT (Hình A.3)
// ----------------------------------------------------------------------------
print("\n=== [A.8 - Kịch bản 4] Multi-document ACID Transaction: COMMIT & ABORT (Hình A.3) ===");

// Phiên (a) COMMIT: Mua nốt 2 đơn vị khi kho còn 2 -> tồn về 0 & lưu đơn 9001
const s1 = db.getMongo().startSession();
s1.startTransaction({
  readConcern: { level: "snapshot" },
  writeConcern: { w: "majority", j: true }
});
const d1 = s1.getDatabase("demo_flashsale");
const res1 = d1.stock.updateOne(
  { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 2 } },
  { $inc: { s_quantity: -2 } }
);
if (res1.modifiedCount === 1) {
  d1.orders.insertOne({ o_id: 9001, o_i_id: 101, qty: 2, status: "COMMITTED" });
  s1.commitTransaction();
  print("==> Phiên (a): COMMIT thành công đơn 9001, tồn kho về 0.");
} else {
  s1.abortTransaction();
}
s1.endSession();

// Phiên (b) ABORT: Chèn trước đơn 9002 rồi trừ kho khi tồn = 0 -> hoàn nguyên toàn bộ
const s2 = db.getMongo().startSession();
s2.startTransaction({
  readConcern: { level: "snapshot" },
  writeConcern: { w: "majority", j: true }
});
const d2 = s2.getDatabase("demo_flashsale");
d2.orders.insertOne({ o_id: 9002, o_i_id: 101, qty: 1, status: "SHOULD_ABORT" });
const res2 = d2.stock.updateOne(
  { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 1 } },
  { $inc: { s_quantity: -1 } }
);
if (res2.modifiedCount === 0) {
  s2.abortTransaction();
  print("==> Phiên (b): Hết hàng -> ABORT giao dịch, hoàn nguyên đơn 9002!");
}
s2.endSession();

print("Tồn kho sau COMMIT & ABORT (kỳ vọng s_quantity = 0):");
printjson(db.stock.findOne({ s_w_id: 1, s_i_id: 101 }));
print("Danh sách orders đã chốt (chỉ còn đơn 9001):");
printjson(db.orders.find().toArray());

// ----------------------------------------------------------------------------
// [A.8 - Kịch bản 5] Linh hoạt lược đồ & Backfill trực tuyến (Hình A.4)
// ----------------------------------------------------------------------------
print("\n=== [A.8 - Kịch bản 5] Đổi lược đồ trực tuyến & Backfill (Hình A.4) ===");
const dbOse = db.getSiblingDB("demo_ose");
dbOse.order_line.drop();

// 1. Tạo các document order_line lịch sử (chưa có ol_discount và ol_mig_state)
dbOse.order_line.insertMany([
  { ol_w_id: 1, ol_d_id: 1, ol_o_id: 1001, ol_number: 1, ol_i_id: 1, ol_quantity: 2 },
  { ol_w_id: 1, ol_d_id: 1, ol_o_id: 1002, ol_number: 1, ol_i_id: 2, ol_quantity: 3 }
]);

// 2. Chèn trực tiếp document mới có sẵn ol_discount & ol_mig_state (không cần ALTER TABLE)
dbOse.order_line.insertOne({
  ol_w_id: 1, ol_d_id: 1, ol_o_id: 3001, ol_number: 1, ol_i_id: 1, ol_quantity: 2,
  ol_discount: 1200, ol_mig_state: "MIGRATED"
});

print("Trạng thái song song 2 phiên bản tài liệu trước khi Backfill (Hình A.4):");
printjson(dbOse.order_line.find().toArray());

// 3. Backfill có điều kiện cho các document cũ chưa chuyển đổi
print("Kết quả Backfill có điều kiện ($ne: 'MIGRATED'):");
printjson(
  dbOse.order_line.updateMany(
    { ol_mig_state: { $ne: "MIGRATED" } },
    { $set: { ol_discount: 500, ol_mig_state: "MIGRATED" } }
  )
);
printjson(dbOse.order_line.find().toArray());

// ----------------------------------------------------------------------------
// [A.8 - Kịch bản 6] Giám sát bộ nhớ đệm WiredTiger & Kết nối (Hình A.5)
// ----------------------------------------------------------------------------
print("\n=== [A.8 - Kịch bản 6] Giám sát WiredTiger Cache (3 GiB) & Kết nối (Hình A.5) ===");
printjson({
  wiredTigerCacheBytes: db.serverStatus().wiredTiger.cache["maximum bytes configured"],
  connections: db.serverStatus().connections,
  activeOpsCount: db.currentOp({ active: true }).inprog.length
});
