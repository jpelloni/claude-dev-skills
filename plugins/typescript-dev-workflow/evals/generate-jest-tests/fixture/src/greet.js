function greet(name, options = {}) {
  if (name == null || String(name).trim() === '') {
    throw new Error('name is required');
  }

  const who = String(name).trim();
  if (options.shout) {
    return `HELLO, ${who.toUpperCase()}!`;
  }
  return `Hello, ${who}.`;
}

module.exports = { greet };
