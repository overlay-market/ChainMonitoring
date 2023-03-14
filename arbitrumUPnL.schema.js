const mongoose = require("mongoose");

const arbitrumUPnLSchema = new mongoose.Schema({
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

// connect arbitrumUPnLSchema with the "arbitrumupnl" collection
module.exports = mongoose.model("arbitrumUPnL", arbitrumUPnLSchema);
