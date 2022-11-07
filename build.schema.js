const mongoose = require("mongoose");

const buildSchema = new mongoose.Schema({
  market: {
    type: String,
    required: true,
  },
  date: {
    type: String,
    required: true,
  },
  capOI: {
    type: Number,
    required: true,
  },
  userOI: {
    type: Number,
    required: true,
  },
  sender: {
    type: String,
    required: true,
  },
  collateralInOVL: {
    type: Number,
    required: true,
  },
  percentageOfCapOiBought: {
    type: Number,
    required: true,
  },
});

// connect buildSchema with the "builds" collection
module.exports = mongoose.model("Build", buildSchema);
