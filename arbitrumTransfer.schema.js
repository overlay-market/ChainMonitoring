const mongoose = require("mongoose");

const arbitrumTransferSchema = new mongoose.Schema({
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

// connect arbitrumTransferSchema with the "arbitrumtransfers" collection
module.exports = mongoose.model("arbitrumTransfer", arbitrumTransferSchema);
