// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title ProposalRegistry
/// @notice Publishes Merkle roots of the "Залуу Дуу Хоолой" ledger on a public chain.
/// Only roots are stored: no proposal text or personal data ever goes on-chain.
/// Anyone can later prove a proposal's block hash was included in a published
/// root using the Merkle proof returned by GET /api/proofs/{block_hash}.
contract ProposalRegistry {
    struct Anchor {
        bytes32 merkleRoot;
        uint64 fromIndex;
        uint64 toIndex;
        uint64 timestamp;
    }

    address public owner;
    Anchor[] public anchors;

    event Anchored(uint256 indexed anchorId, bytes32 merkleRoot, uint64 fromIndex, uint64 toIndex);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /// @notice Record a Merkle root covering ledger blocks [fromIndex, toIndex].
    function anchor(bytes32 merkleRoot, uint64 fromIndex, uint64 toIndex) external onlyOwner returns (uint256 id) {
        require(toIndex >= fromIndex, "bad range");
        if (anchors.length > 0) {
            require(fromIndex == anchors[anchors.length - 1].toIndex + 1, "range must continue previous anchor");
        }
        anchors.push(Anchor(merkleRoot, fromIndex, toIndex, uint64(block.timestamp)));
        id = anchors.length - 1;
        emit Anchored(id, merkleRoot, fromIndex, toIndex);
    }

    function anchorCount() external view returns (uint256) {
        return anchors.length;
    }

    /// @notice Verify a SHA-256 Merkle proof against a stored root (same scheme as backend/app/ledger.py).
    /// @param leaf      block hash
    /// @param siblings  sibling hashes from leaf to root
    /// @param isLeft    true when the sibling is on the left at that level
    function verify(uint256 anchorId, bytes32 leaf, bytes32[] calldata siblings, bool[] calldata isLeft)
        external view returns (bool)
    {
        require(siblings.length == isLeft.length, "length mismatch");
        bytes32 h = leaf;
        for (uint256 i = 0; i < siblings.length; i++) {
            h = isLeft[i] ? _hashPair(siblings[i], h) : _hashPair(h, siblings[i]);
        }
        return h == anchors[anchorId].merkleRoot;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero address");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    /// Backend hashes the concatenated lowercase hex strings with SHA-256, so we do the same.
    function _hashPair(bytes32 a, bytes32 b) private pure returns (bytes32) {
        return sha256(abi.encodePacked(_toHex(a), _toHex(b)));
    }

    function _toHex(bytes32 data) private pure returns (bytes memory out) {
        bytes16 hexChars = "0123456789abcdef";
        out = new bytes(64);
        for (uint256 i = 0; i < 32; i++) {
            out[2 * i] = hexChars[uint8(data[i] >> 4)];
            out[2 * i + 1] = hexChars[uint8(data[i] & 0x0f)];
        }
    }
}
