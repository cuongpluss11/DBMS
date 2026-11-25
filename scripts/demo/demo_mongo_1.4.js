// ============================================================================
// KỊCH BẢN KIỂM CHỨNG CHỨC NĂNG CƠ BẢN MONGODB 8.0.20 (MỤC 1.4 & PHỤ LỤC A.8)
// Chuẩn hóa theo 3 câu hỏi: Thực hiện gì -> Quan sát được gì (trước/sau) -> Chứng minh cơ chế gì
// Công cụ: MongoDB Compass (tab >_ MONGOSH) hoặc mongosh CLI
// Kết nối: mongodb://127.0.0.1:27018/?directConnection=true
// ============================================================================

// ----------------------------------------------------------------------------
// [Demo A1] Khởi tạo kết nối, kiểm chứng phiên bản & Replica Set
// Cơ chế chứng minh: Xác nhận phiên bản 8.0.20 và Replica Set 1 nút đang là PRIMARY
// (điều kiện bắt buộc để vận hành Multi-document ACID Transaction).
// ----------------------------------------------------------------------------
print("=== [A1] Kiểm chứng phiên bản & trạng thái Replica Set ===");
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
// [Demo A2] CRUD cơ bản trên mô hình Document BSON (demo_flashsale)
// Cơ chế chứng minh: Lưu trữ, truy vấn theo bộ lọc và xóa tài liệu BSON.
// ----------------------------------------------------------------------------
print("\n=== [A2] CRUD cơ bản trên Document BSON ===");
db = db.getSiblingDB("demo_flashsale");
db.item.drop();
db.stock.drop();
db.orders.drop();

// 1. CREATE: Thêm sản phẩm, tồn kho ban đầu (s_quantity = 5) và 1 đơn kiểm thử
const insItem = db.item.insertOne({ i_id: 101, i_name: "Tai nghe Flash-Sale", i_price: 500000 });
const insStock = db.stock.insertOne({ s_w_id: 1, s_i_id: 101, s_quantity: 5 });
const insOrder = db.orders.insertOne({ o_id: 9000, o_i_id: 101, qty: 1, status: "TEST_CRUD" });
print("Kết quả insertOne:", tojson({ item: insItem.acknowledged, stock: insStock.acknowledged, order: insOrder.acknowledged }));

// 2. READ: Truy vấn tài liệu BSON trước khi xóa đơn kiểm thử
print("Truy vấn item & stock vừa tạo:");
printjson(db.item.findOne({ i_id: 101 }, { _id: 0 }));
printjson(db.stock.findOne({ s_w_id: 1, s_i_id: 101 }, { _id: 0 }));
print("Đơn kiểm thử trước khi xóa:");
printjson(db.orders.findOne({ o_id: 9000 }, { _id: 0 }));

// 3. DELETE & Trạng thái cuối cùng: Xóa đơn kiểm thử 9000, giữ tồn kho = 5 cho Demo A3
const delOrder = db.orders.deleteOne({ o_id: 9000 });
print("Kết quả deleteOne:", tojson(delOrder));
print("Trạng thái orders sau khi xóa (kỳ vọng rỗng []):", tojson(db.orders.find().toArray()));

// ----------------------------------------------------------------------------
// [Demo A3] Cập nhật nguyên tử có điều kiện — Chống âm kho (tồn: 5 -> 2 -> 2)
// Cơ chế chứng minh: Tính nguyên tử cấp đơn tài liệu (điều kiện lọc $gte và phép $inc
// được đánh giá trong cùng một thao tác ghi, ngăn trừ vượt tồn kho).
// ----------------------------------------------------------------------------
print("\n=== [A3] Cập nhật nguyên tử có điều kiện (5 -> 2 -> 2) ===");
print("0. Trạng thái tồn kho TRƯỚC cập nhật:");
printjson(db.stock.findOne({ s_w_id: 1, s_i_id: 101 }, { _id: 0 }));

// (a) Mua 3 khi tồn kho còn 5 -> thỏa điều kiện (5 >= 3): modifiedCount = 1, tồn còn 2
const updOk = db.stock.updateOne(
  { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 3 } },
  { $inc: { s_quantity: -3 } }
);
print("1. Lần (a) mua 3 khi còn 5 -> Kết quả updateOne & tồn kho sau lần (a):");
printjson(updOk);
printjson(db.stock.findOne({ s_w_id: 1, s_i_id: 101 }, { _id: 0 }));

// (b) Mua 4 khi tồn kho chỉ còn 2 -> không thỏa (2 < 4): modifiedCount = 0, tồn giữ nguyên 2
const updReject = db.stock.updateOne(
  { s_w_id: 1, s_i_id: 101, s_quantity: { $gte: 4 } },
  { $inc: { s_quantity: -4 } }
);
print("2. Lần (b) mua 4 khi còn 2 -> Kết quả updateOne & trạng thái tồn kho CUỐI CÙNG:");
printjson(updReject);
printjson(db.stock.findOne({ s_w_id: 1, s_i_id: 101 }, { _id: 0 }));

// ----------------------------------------------------------------------------
// [Demo A4] Giao dịch ACID nhiều tài liệu — Quan sát rõ trạng thái sau COMMIT & sau ABORT
// Cơ chế chứng minh: Tính nguyên tử xuyên nhiều collection (stock + orders) với
// readConcern: "snapshot" và writeConcern: { w: "majority", j: true }.
// ----------------------------------------------------------------------------
print("\n=== [A4] Multi-document ACID Transaction (COMMIT & ABORT) ===");

// --- Phiên (a) COMMIT: Mua nốt 2 đơn vị khi kho còn 2 -> tồn về 0 & lưu đơn 9001 ---
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
} else {
  s1.abortTransaction();
}
s1.endSession();

print("1. Trạng thái dữ liệu NGAY SAU COMMIT (Phiên a):");
print("   stock:", tojson(db.stock.findOne({ s_w_id: 1, s_i_id: 101 }, { _id: 0 })));
print("   orders:", tojson(db.orders.find({}, { _id: 0 }).toArray()));

// --- Phiên (b) ABORT: Chèn đơn 9002 trước, sau đó trừ kho thất bại (tồn = 0) -> hủy giao dịch ---
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
}
s2.endSession();

print("2. Trạng thái dữ liệu NGAY SAU ABORT (Phiên b - đơn 9002 bị hoàn nguyên hoàn toàn):");
print("   stock:", tojson(db.stock.findOne({ s_w_id: 1, s_i_id: 101 }, { _id: 0 })));
print("   orders:", tojson(db.orders.find({}, { _id: 0 }).toArray()));

// ----------------------------------------------------------------------------
// [Demo A5] Schema Evolution — Linh hoạt lược đồ & Backfill dữ liệu lịch sử
// Lưu ý học thuật: Demo này xác nhận tính linh hoạt lược đồ (hai phiên bản cấu trúc
// document cùng tồn tại mà không cần ALTER TABLE) và khả năng cập nhật bổ sung trường mới;
// tác động đồng thời/hiệu năng dưới tải cao được đánh giá riêng tại Phần 2 (Mục 2.6).
// ----------------------------------------------------------------------------
print("\n=== [A5] Schema Evolution: Linh hoạt lược đồ & Backfill ===");
const dbOse = db.getSiblingDB("demo_ose");
dbOse.order_line.drop();

// 1. Tạo các document lịch sử theo cấu trúc cũ (chưa có ol_discount và ol_mig_state)
dbOse.order_line.insertMany([
  { ol_w_id: 1, ol_d_id: 1, ol_o_id: 1001, ol_number: 1, ol_i_id: 1, ol_quantity: 2 },
  { ol_w_id: 1, ol_d_id: 1, ol_o_id: 1002, ol_number: 1, ol_i_id: 2, ol_quantity: 3 }
]);

// 2. Ghi trực tiếp document mới có thêm trường ol_discount và ol_mig_state
dbOse.order_line.insertOne({
  ol_w_id: 1, ol_d_id: 1, ol_o_id: 3001, ol_number: 1, ol_i_id: 1, ol_quantity: 2,
  ol_discount: 1200, ol_mig_state: "MIGRATED"
});

print("1. Trạng thái TRƯỚC Backfill (document cũ thiếu ol_discount và document mới cùng tồn tại):");
printjson(dbOse.order_line.find({}, { _id: 0 }).toArray());

// 3. Backfill có điều kiện các document lịch sử chưa chuyển đổi
const migRes = dbOse.order_line.updateMany(
  { ol_mig_state: { $ne: "MIGRATED" } },
  { $set: { ol_discount: 500, ol_mig_state: "MIGRATED" } }
);
print("2. Kết quả updateMany Backfill & trạng thái dữ liệu SAU chuyển đổi:");
printjson(migRes);
printjson(dbOse.order_line.find({}, { _id: 0 }).toArray());

// ----------------------------------------------------------------------------
// [Demo A6] Giám sát vận hành — Cấu hình WiredTiger Cache (3 GiB) & Kết nối
// Cơ chế chứng minh: Xác nhận tham số --wiredTigerCacheSizeGB=3 (3,221,225,472 byte)
// và khả năng quan sát kết nối, thao tác đang hoạt động trên động cơ lưu trữ WiredTiger.
// ----------------------------------------------------------------------------
print("\n=== [A6] Giám sát cấu hình WiredTiger Cache & Kết nối ===");
printjson({
  wiredTigerCacheBytes: db.serverStatus().wiredTiger.cache["maximum bytes configured"],
  connections: db.serverStatus().connections,
  activeOpsCount: db.currentOp({ active: true }).inprog.length
});
