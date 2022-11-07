const mongoose = require("mongoose");

const transferSchema = new mongoose.Schema({
  market: {
    type: String,
    required: true,
  },
  date: {
    type: String,
    required: true,
  },
  totalMintedOVLInMarket: {
    type: Number,
    required: true,
  },
  totalBurntOVLInMarket: {
    type: Number,
    required: true,
  },
});

// connect transferSchema with the "transfers" collection
module.exports = mongoose.model("Transfer", transferSchema);
