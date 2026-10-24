function approach(_a, _b, _amount) {
    return _a < _b ? min(_a + _amount, _b) : max(_a - _amount, _b);
}
