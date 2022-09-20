#ifndef VPX_VPX_PORTS_MISC_H_
#define VPX_VPX_PORTS_MISC_H_

/*!\brief Bit depth for codec
 * *
 * This enumeration determines the bit depth of the codec.
 */
typedef enum vpx_bit_depth {
  VPX_BITS_8 = 8,   /**<  8 bits */
  VPX_BITS_10 = 10, /**< 10 bits */
  VPX_BITS_12 = 12, /**< 12 bits */
} vpx_bit_depth_t;

#endif
