addi 1, 0, 0
addi 2, 0, 7
mtspr 9, 2       /* set ctr to 7 */
addi 1, 1, 5
bc 16, 0, -0x4  /* bdnz to the addi above */
