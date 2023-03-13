const mongoose = require("mongoose");

const transferSchema = new mongoose.Schema({
  date: {
    type: String,
    required: true,
  },
  market: {
    type: String,
    required: true,
  },
  lastBlockNumber: {
    type: Number,
    required: true,
  },
  totalBurntOVLInMarket: {
    type: Number,
    required: true,
  },
  totalMintedOVLInMarket: {
    type: Number,
    required: true,
  },
});

// connect transferSchema with the "transfers" collection
module.exports = mongoose.model("Transfer", transferSchema);
