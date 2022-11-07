const mongoose = require("mongoose");

const uPnLSchema = new mongoose.Schema({
  market: {
    type: String,
    required: true,
  },
  date: {
    type: String,
    required: true,
  },
  totalUnrealizedProfit: {
    type: Number,
    required: true,
  },
  totalUnrealizedLoss: {
    type: Number,
    required: true,
  },
});

// connect uPnLSchema with the "upnls" collection
module.exports = mongoose.model("uPnL", uPnLSchema);
