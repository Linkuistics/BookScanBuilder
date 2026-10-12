/* Literal declared positive/negative values are compiled by the acceptance runner. */
#ifndef LEAF_VALUE
#error "Declare the independently expected leaf value before executing the probe"
#endif
int bookscan_leaf_value(void) { return LEAF_VALUE; }
